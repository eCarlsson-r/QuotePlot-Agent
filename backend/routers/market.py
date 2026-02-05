from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, select, text as sql_text
from brain import analyze_divergence
from database import get_db
from models import TokenMap, Stock  # Ensure these are your model classes
from utils import get_tokens

router = APIRouter(prefix="/api/market", tags=["market"])

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

@router.get("/insight/{symbol}")
async def get_token_insight(symbol: str, db: Session = Depends(get_db)):
    insight = analyze_divergence(db, symbol.upper())
    return {"symbol": symbol, "insight": insight}