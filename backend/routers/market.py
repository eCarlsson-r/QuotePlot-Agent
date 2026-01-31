import asyncio
import httpx
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import text as sql_text
from database import get_db, SessionLocal
from datetime import datetime, timedelta

router = APIRouter(
    prefix="/api/market",
    tags=["market"]
)

# Map your symbols to Pyth Feed IDs
PRICE_FEED_IDS = {
    "BTC": "0xe62df6c8b4a85fe1a67db44dc12de5db330f7ac66b72dc658afedf0f4a415b43",
    "ETH": "0xff61491a931112ddf1bd8147cd1b641375f79f5825126d665480874634fd0ace"
}

sync_progress_store = {}

async def get_latest_pyth_price(symbol: str):
    """Utility function to fetch the most recent price from Pyth Hermes."""
    price_id = PRICE_FEED_IDS.get(symbol)
    if not price_id:
        return None
        
    url = f"https://hermes.pyth.network/v2/updates/price/latest?ids[]={price_id}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                p = data['parsed'][0]['price']
                # Price * 10^expo (Pyth standard)
                return float(p['price']) * (10 ** p['expo'])
        except Exception as e:
            print(f"❌ Oracle fetch failed for {symbol}: {e}")
    return None

# Replaces stockChart.php logic
@router.get("/stock/{symbol}")
def get_stock_details(symbol: str, db: Session = Depends(get_db)):
    query = sql_text("""
        SELECT DISTINCT open, price, high, low, volume, datetime 
        FROM stocks 
        WHERE symbol = :s 
        ORDER BY datetime ASC
    """)
    result = db.execute(query, {"s": symbol}).mappings().all()
    
    if not result:
        raise HTTPException(status_code=404, detail="Stock symbol not found")
        
    return result

# Replaces marketChart.php logic
@router.get("/overview")
def get_market_overview(db: Session = Depends(get_db)):
    # First, get distinct symbols as done in legacy PHP
    symbols_query = sql_text("SELECT DISTINCT symbol FROM stocks")
    symbols = db.execute(symbols_query).scalars().all()
    
    all_stats = {}
    for sym in symbols:
        # Get history for each symbol
        data_query = sql_text("""
            SELECT DISTINCT price, volume, datetime 
            FROM stocks 
            WHERE symbol = :s 
            ORDER BY datetime ASC
        """)
        all_stats[sym] = db.execute(data_query, {"s": sym}).mappings().all()
        
    return all_stats

@router.get("/tickers")
async def get_all_tickers(db: Session = Depends(get_db)):
    # Fetch latest and second-to-latest price for every symbol to calculate change
    query = sql_text("""
        SELECT symbol, price, datetime 
        FROM (
            SELECT symbol, price, datetime,
            ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY datetime DESC) as rn
            FROM stocks
        ) t WHERE rn <= 2
    """)
    rows = db.execute(query).mappings().all()
    
    # Process rows into a dictionary: { "BTC": {"price": 42000, "change": 1.2}, ... }
    tickers = {}
    for row in rows:
        sym = row['symbol']
        if sym not in tickers:
            tickers[sym] = {"current": float(row['price']), "prev": None}
        else:
            tickers[sym]["prev"] = float(row['price'])
            
    # Calculate % change
    result = {}
    for sym, prices in tickers.items():
        change = 0
        if prices['prev']:
            change = ((prices['current'] - prices['prev']) / prices['prev']) * 100
        result[sym] = {"price": prices['current'], "change": change}
        
    return result

@router.get("/sync-status/{symbol}")
async def get_sync_status(symbol: str):
    return {"progress": sync_progress_store.get(symbol, 0)}

async def backfill_history(symbol: str, start_dt: datetime):
    """Fills the gap from start_dt to now in 1-hour increments."""
    price_id = PRICE_FEED_IDS[symbol]
    now = datetime.now()
    total_hours = int((now - start_dt).total_seconds() / 3600)
    hours_completed = 0
    
    sync_progress_store[symbol] = 0

    async with httpx.AsyncClient() as client:
        current_time = start_dt
        while current_time < now:
            ts = int(current_time.timestamp())
            # Pyth Benchmarks API
            url = f"https://hermes.pyth.network/v1/updates/price/{ts}?ids[]={price_id}"
            
            try:
                res = await client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    p = data['parsed'][0]['price']
                    # Apply Pyth exponent
                    final_price = float(p['price']) * (10 ** p['expo'])
                    dt_str = datetime.fromtimestamp(p['publish_time']).strftime('%Y-%m-%d %H:%M:%S')

                    with SessionLocal() as db:
                        # Use ON DUPLICATE KEY to prevent crashes on overlap
                        db.execute(sql_text("""
                            INSERT INTO stocks (symbol, price, datetime) 
                            VALUES (:s, :p, :dt)
                            ON DUPLICATE KEY UPDATE price = VALUES(price)
                        """), {"s": symbol, "p": final_price, "dt": dt_str})
                        db.commit()
            except Exception as e:
                print(f"❌ Backfill failed at {dt_str}: {e}")
            
            hours_completed += 1
            # Update progress percentage
            sync_progress_store[symbol] = int((hours_completed / total_hours) * 100)
        
            current_time += timedelta(hours=1)
            await asyncio.sleep(0.05) # Rate limit respect
        sync_progress_store[symbol] = 100

async def sync_oracle_task(symbol: str):
    # 1. Check for data gaps
    with SessionLocal() as db:
        last_entry = db.execute(
            sql_text("SELECT datetime FROM stocks WHERE symbol = :s ORDER BY datetime DESC LIMIT 1"),
            {"s": symbol}
        ).fetchone()

    # 2. Trigger backfill if gap > 2 hours
    if last_entry:
        last_dt = last_entry[0]
        if datetime.now() - last_dt > timedelta(hours=2):
            print(f"🔍 Gap detected for {symbol}. Last data: {last_dt}. Backfilling...")
            # Run history sync as a separate task to avoid blocking live updates
            asyncio.create_task(backfill_history(symbol, last_dt))

    # 3. Proceed with live Pyth sync (your existing v2/updates/price/latest logic)
    final_price = get_latest_pyth_price(symbol);
    with SessionLocal() as db:
        query = sql_text("""
            INSERT INTO stocks (symbol, price, datetime) 
            VALUES (:s, :p, NOW())
        """)
        db.execute(query, {"s": symbol, "p": final_price})
        db.commit()
    print(f"✅ {symbol} synced: ${final_price}")

async def sync_historical_prices(symbol: str, days_back: int = 4):
    price_id = PRICE_FEED_IDS[symbol]
    # Calculate how many 1-hour intervals we need to fill
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days_back)
    
    async with httpx.AsyncClient() as client:
        current_time = start_time
        while current_time < end_time:
            timestamp = int(current_time.timestamp())
            # Pyth Benchmarks endpoint for a specific timestamp
            url = f"https://hermes.pyth.network/v1/updates/price/{timestamp}?ids[]={price_id}"
            
            response = await client.get(url)
            if response.status_code == 200:
                data = response.json()
                # Benchmarks structure is slightly different than /latest
                p = data['parsed'][0]['price']
                final_price = float(p['price']) * (10 ** p['expo'])
                
                # Use the timestamp from the metadata to be precise
                dt_str = datetime.fromtimestamp(p['publish_time']).strftime('%Y-%m-%d %H:%M:%S')

                with SessionLocal() as db:
                    # 'INSERT IGNORE' or checking existence prevents duplicates
                    query = sql_text("""
                        INSERT INTO stocks (symbol, price, datetime) 
                        VALUES (:s, :p, :dt)
                        ON DUPLICATE KEY UPDATE price=price
                    """)
                    db.execute(query, {"s": symbol, "p": final_price, "dt": dt_str})
                    db.commit()
            
            # Move forward by 1 hour (3600 seconds) to avoid over-polling
            current_time += timedelta(hours=1)
            await asyncio.sleep(0.1) # Rate limit protection
            
    print(f"✅ Historical sync complete for {symbol}")

@router.post("/sync-all-history")
async def sync_all(background_tasks: BackgroundTasks):
    def run_sync():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        for symbol in PRICE_FEED_IDS.keys():
            loop.run_until_complete(backfill_history(symbol))

    background_tasks.add_task(run_sync)
    return {"message": "Historical backfill started for all symbols."}

async def continuous_oracle_sync():
    for symbol in PRICE_FEED_IDS.keys():
        # 1. Fetch from Pyth
        price = await get_latest_pyth_price(symbol) 
        if price:
            # 2. Insert into MySQL
            with SessionLocal() as db:
                db.execute(sql_text("""
                    INSERT INTO stocks (symbol, price, datetime) 
                    VALUES (:s, :p, NOW())
                """), {"s": symbol, "p": price})
                db.commit()
        
        print(f"📡 Oracle Saved: {symbol} at {price}")