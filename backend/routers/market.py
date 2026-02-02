import asyncio
import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text as sql_text
from datetime import datetime, timedelta

from database import get_db, SessionLocal, TokenMap

# --- SHARED STATE ---
PRICE_FEED_IDS = {
    "BTC": "0xe62df6c8b4a85fe1a67db44dc12de5db330f7ac66b72dc658afedf0f4a415b43",
    "ETH": "0xff61491a931112ddf1bd8147cd1b641375f79f5825126d665480874634fd0ace"
}
sync_progress_store = {}
http_client: httpx.AsyncClient = None  # Global client initialized in lifespan

router = APIRouter(prefix="/api/market", tags=["market"])

# --- UTILITIES (The "Clean" Core) ---

async def fetch_pyth_price(symbol: str, timestamp: int = None):
    """Universal fetcher for both LIVE and HISTORICAL Pyth data."""
    feed_id = PRICE_FEED_IDS.get(symbol)
    if not feed_id: return None
    
    # Use v1 for historical benchmarks, v2 for latest updates
    url = f"https://hermes.pyth.network/v1/updates/price/{timestamp}?ids[]={feed_id}" if timestamp \
          else f"https://hermes.pyth.network/v2/updates/price/latest?ids[]={feed_id}"
    
    try:
        response = await http_client.get(url, timeout=5.0)
        if response.status_code == 200:
            data = response.json()
            p = data['parsed'][0]['price']
            return float(p['price']) * (10 ** p['expo'])
    except Exception as e:
        print(f"⚠️ Pyth Fetch Error ({symbol}): {e}")
    return None

def db_save_price(symbol: str, price: float, dt: str, db: Session):
    """Unified database saver with conflict resolution."""
    query = sql_text("""
        INSERT INTO stocks (symbol, price, datetime) 
        VALUES (:s, :p, :dt)
        ON DUPLICATE KEY UPDATE price = VALUES(price)
    """)
    db.execute(query, {"s": symbol, "p": price, "dt": dt})
    db.commit()

# --- ENDPOINTS ---

@router.get("/discovery")
async def discover_web3_tokens(db: Session = Depends(get_db)):
    # 1. Fetch live "Web3" list from CoinGecko
    # (Using the get_tokens() function you already have)
    gecko_list = await get_tokens()
    
    # 2. Get our local "Pro" mappings from the DB
    mappings = db.query(TokenMap).all()
    pyth_lookup = {m.symbol: m.pyth_id for m in mappings if m.pyth_id}

    # 3. Enrich the list
    enriched_list = []
    for coin in gecko_list:
        symbol = coin['symbol'].upper()
        enriched_list.append({
            "name": coin['name'],
            "symbol": symbol,
            "image": coin['image'],
            "current_price": coin['current_price'],
            "has_pro_feed": symbol in pyth_lookup, # Flag for Lucy to "Unlock" Pro Chart
            "pyth_id": pyth_lookup.get(symbol)
        })
    
    return enriched_list

async def get_tokens():
    # Use 'async with' to ensure the connection is closed automatically
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.coingecko.com/api/v3/coins/markets",
            params={"vs_currency": "usd", "category": "web3"}
        )
        return response.json()
    
@router.get("/web3-list")
async def get_web3_token_list():
    # 1. Fetch the general Web3 list from CoinGecko
    tokens = await get_tokens() 
    
    # 2. Tag tokens that have high-speed Pyth feeds available
    for token in tokens:
        symbol = token['symbol'].upper()
        token['has_pro_feed'] = symbol in PRICE_FEED_IDS
        token['pyth_id'] = PRICE_FEED_IDS.get(symbol)
        
    return tokens

@router.get("/history/{symbol}")
async def get_history(symbol: str, db: Session = Depends(get_db)):
    """The fuel for your amCharts visual."""
    query = sql_text("""
        SELECT price, datetime FROM stocks 
        WHERE symbol = :s ORDER BY datetime ASC LIMIT 1000
    """)
    rows = db.execute(query, {"s": symbol}).mappings().all()
    return [{"datetime": int(r['datetime'].timestamp() * 1000), "price": float(r['price'])} for r in rows]

@router.get("/tickers")
async def get_tickers(db: Session = Depends(get_db)):
    """Fast summary for the sidebar list."""
    query = sql_text("""
        SELECT symbol, price, datetime FROM (
            SELECT symbol, price, datetime,
            ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY datetime DESC) as rn
            FROM stocks
        ) t WHERE rn <= 2
    """)
    rows = db.execute(query).mappings().all()
    
    res = {}
    for r in rows:
        s = r['symbol']
        if s not in res: res[s] = {"price": float(r['price']), "prev": None}
        else: res[s]["prev"] = float(r['price'])
        
    return {s: {"price": d["price"], "change": ((d["price"]-d["prev"])/d["prev"]*100) if d["prev"] else 0} 
            for s, d in res.items()}

# --- BACKGROUND TASKS ---

async def backfill_history_task(symbol: str, start_dt: datetime):
    """Unified backfiller with progress tracking."""
    now = datetime.now()
    total_steps = int((now - start_dt).total_seconds() / 3600)
    
    for i in range(total_steps):
        current_ts = int((start_dt + timedelta(hours=i)).timestamp())
        price = await fetch_pyth_price(symbol, current_ts)
        if price:
            with SessionLocal() as db:
                dt_str = datetime.fromtimestamp(current_ts).strftime('%Y-%m-%d %H:%M:%S')
                db_save_price(symbol, price, dt_str, db)
        
        sync_progress_store[symbol] = int(((i + 1) / total_steps) * 100)
        await asyncio.sleep(0.05) # Be kind to the API
    sync_progress_store[symbol] = 100