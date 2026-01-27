
import httpx
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import text as sql_text
from database import get_db

router = APIRouter(
    prefix="/api/market",
    tags=["market"]
)

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

@router.post("/sync/{symbol}")
async def trigger_sync(symbol: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(sync_oracle_task, symbol)
    return {"status": "Syncing started"}

async def sync_oracle_task(symbol: str):
    # Oracle 'crawling' logic here...
    print(f"Syncing {symbol} from Oracle to MySQL...")

# Mapping your simple symbols to Pyth Price Feed IDs
# BTC/USD example: 0xe62df6c8b4a85fe1a67db44dc12de5db330f7ac66b72dc658afedf0f4a415b43
PRICE_FEED_IDS = {
    "BTC": "0xe62df6c8b4a85fe1a67db44dc12de5db330f7ac66b72dc658afedf0f4a415b43",
    "ETH": "0xff61491a931112ddf1bd8147cd1b641375f79f5825126d665480874634fd0ace"
}

@router.post("/sync/{symbol}")
async def trigger_sync(symbol: str, background_tasks: BackgroundTasks):
    symbol_up = symbol.upper()
    if symbol_up not in PRICE_FEED_IDS:
        return {"error": "Symbol not supported by Oracle yet"}
        
    # Schedule the crawl task
    background_tasks.add_task(sync_oracle_task, symbol_up)
    return {"status": f"Sync started for {symbol_up}"}

async def sync_oracle_task(symbol: str):
    price_id = PRICE_FEED_IDS[symbol]
    url = f"https://hermes.pyth.network/v2/updates/price/latest?ids[]={price_id}"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code == 200:
            data = response.json()
            # Pyth prices are integers; must apply the 'exponent' to get decimal
            p = data['parsed'][0]['price']
            final_price = float(p['price']) * (10 ** p['expo'])
            
            # Save to MySQL (Manual session management inside background task)
            from database import SessionLocal
            with SessionLocal() as db:
                query = sql_text("""
                    INSERT INTO stocks (symbol, price, datetime) 
                    VALUES (:s, :p, NOW())
                """)
                db.execute(query, {"s": symbol, "p": final_price})
                db.commit()
            print(f"✅ {symbol} synced: ${final_price}")