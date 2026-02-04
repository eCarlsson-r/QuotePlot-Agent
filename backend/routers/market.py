import time
import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, select, text as sql_text
from database import get_db
from models import TokenMap, Stock  # Ensure these are your model classes
from utils import get_tokens

router = APIRouter(prefix="/api/market", tags=["market"])

# --- SHARED STATE ---
http_client: httpx.AsyncClient = None  # Global client initialized in lifespan
async def get_client():
    global http_client
    if http_client is None or http_client.is_closed:
        http_client = httpx.AsyncClient(timeout=10.0)
    return http_client

# --- ENDPOINTS ---

@router.get("/web3-list")
async def get_web3_token_list(db: Session = Depends(get_db)):
    # 1. Fetch live "Discovery" list from CoinGecko
    tokens = await get_tokens() 
    
    # 2. Get active mappings from our DB
    mappings = db.query(TokenMap).filter(TokenMap.is_active == True).all()
    pyth_lookup = {m.symbol: m.pyth_id for m in mappings}

    # 3. Enrich the data for the Frontend
    for token in tokens:
        symbol = token.symbol.upper()
        pyth_id = pyth_lookup.get(symbol)
        
        token.has_pro_feed = pyth_id is not None
        token.pyth_id = pyth_id
        
    return tokens

@router.get("/history/{symbol}")
async def get_history(symbol: str, db: Session = Depends(get_db)):
    """Provides data for amCharts visuals."""
    query = sql_text("SELECT price, datetime FROM stocks WHERE symbol = :s ORDER BY datetime ASC LIMIT 1000")
    rows = db.execute(query, {"s": symbol}).mappings().all()
    return [{"datetime": int(r['datetime'].timestamp() * 1000), "price": float(r['price'])} for r in rows]

@router.get("/tickers")
async def get_all_tickers(db: Session = Depends(get_db)):
    # 1. Create a "Ranked" subquery to find the 2 most recent prices per symbol
    # This replaces the need for separate loops or hardcoded dicts
    ranked_subquery = (
        select(
            Stock.symbol,
            Stock.price,
            func.row_number().over(
                partition_by=Stock.symbol, 
                order_by=Stock.datetime.desc()
            ).label("rn")
        )
        .where(Stock.symbol.in_(select(TokenMap.symbol).where(TokenMap.is_active == True)))
        .subquery()
    )

    # 2. Fetch only the top 2 rows (current and previous)
    query = select(ranked_subquery).where(ranked_subquery.c.rn <= 2)
    rows = db.execute(query).mappings().all()

    # 3. Format into { "BTC": {"price": 100, "change": 1.5}, ... }
    tickers = {}
    for row in rows:
        sym = row['symbol']
        price = float(row['price'])
        
        if sym not in tickers:
            tickers[sym] = {"current": price, "prev": None}
        else:
            tickers[sym]["prev"] = price

    # 4. Final calculation
    result = {}
    for sym, p in tickers.items():
        change = 0
        if p['prev'] and p['prev'] != 0:
            change = ((p['current'] - p['prev']) / p['prev']) * 100
        
        result[sym] = {
            "price": p['current'],
            "change": round(change, 2)
        }

    return result


# --- UTILITIES (The "Clean" Core) ---

async def fetch_pyth_price(price_id: str):
    # Pyth Hermes V2 endpoint
    url = "https://hermes.pyth.network/v2/updates/price/latest"
    # Pass params as a dict to let the library handle the [] encoding
    params = {"ids[]": [price_id]}

    try:
        client = await get_client()
        response = await client.get(url, params=params)
        if response.status_code != 200:
            return None
        data = response.json()
        
        # Safe traversal of the Pyth JSON structure
        if "parsed" in data and len(data["parsed"]) > 0:
            p = data["parsed"][0].get("price", {})
            publish_time = p.get("publish_time")

            # Check if stale (e.g., older than 24 hours)
            if (int(time.time()) - publish_time) > 86400:
                print(f"⚠️ Feed {price_id} is stale.")
                return "STALE" # Return a unique string to signal deletion

            raw_price = float(p.get("price", 0))
            expo = int(p.get("expo", 0))

            if raw_price != 0:
                return raw_price * (10 ** expo)
        
        return None # Explicitly return None if data is missing
    except httpx.ConnectError:
        print("❌ Connection Error: Could not reach Pyth servers.")
    except httpx.TimeoutException:
        print("❌ Timeout Error: Pyth took too long to respond.")
    except Exception as e:
        print(f"❌ Unexpected Error during fetch: {type(e).__name__} - {e}")
    return None