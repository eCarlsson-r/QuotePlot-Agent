"""
routers/market.py — Market data endpoints

Bright Data integration:
  /web3-list  → get_tokens() fetches Pyth + CoinGecko through the BD-proxied
                client (ACCESS layer in utils.py), so the discovery call is
                never blocked by CoinGecko's per-IP rate limits.
  /insight    → analyze_divergence() is CPU-bound DB work; runs fine on the
                event loop (no I/O blocking).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, select
from sqlalchemy import text as sql_text

from brain import analyze_divergence
from database import get_db
from models import Stock, TokenMap
from utils import get_tokens

router = APIRouter(prefix="/api/market", tags=["market"])


# ---------------------------------------------------------------------------
# /web3-list
# ---------------------------------------------------------------------------

@router.get("/web3-list")
async def get_web3_token_list(db: Session = Depends(get_db)):
    """
    Returns the full Pyth/CoinGecko token universe enriched with DB metadata.

    FIX: get_tokens() can return None (both upstream APIs failed).  The old
    code iterated over None and raised an unhandled TypeError that produced a
    500 with no useful message.  Now returns a 503 with a clear reason.

    FIX: token objects returned by get_tokens() are plain dicts, not ORM
    instances, so attribute assignment (token.has_pro_feed = ...) silently
    did nothing and the fields were absent from the response.  Fixed to mutate
    the dict directly.
    """
    tokens = await get_tokens()

    if tokens is None:
        raise HTTPException(
            status_code=503,
            detail="Token discovery unavailable: upstream Pyth/CoinGecko fetch failed.",
        )

    mappings    = db.query(TokenMap).filter(TokenMap.is_active == True).all()
    pyth_lookup = {m.symbol: m.pyth_id for m in mappings}

    for token in tokens:                        # token is a dict
        symbol                  = token["symbol"].upper()
        pyth_id                 = pyth_lookup.get(symbol)
        token["has_pro_feed"]   = pyth_id is not None
        token["pyth_id"]        = pyth_id       # overwrite with DB value (may differ)

    return tokens


# ---------------------------------------------------------------------------
# /history/{symbol}
# ---------------------------------------------------------------------------

@router.get("/history/{symbol}")
async def get_history(symbol: str, db: Session = Depends(get_db)):
    """
    Provides OHLC-style price history for amCharts visuals.

    FIX: symbol is passed straight from the URL into a raw SQL query via a
    parameterised placeholder (:s) — that part is safe.  But the symbol was
    not normalised to uppercase, so "btc" and "BTC" returned different (empty
    vs populated) result sets depending on how the token was seeded.
    """
    query = sql_text(
        "SELECT price, datetime FROM stocks "
        "WHERE symbol = :s ORDER BY datetime ASC LIMIT 1000"
    )
    rows = db.execute(query, {"s": symbol.upper()}).mappings().all()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No price history found for '{symbol.upper()}'.",
        )

    return [
        {
            "datetime": int(r["datetime"].timestamp() * 1000),
            "price":    float(r["price"]),
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# /tickers
# ---------------------------------------------------------------------------

@router.get("/tickers")
async def get_all_tickers(db: Session = Depends(get_db)):
    """
    Returns { "BTC": {"price": 100.0, "change": 1.5}, ... } for the ticker bar.

    The window-function approach (row_number OVER partition) is correct and
    efficient — kept as-is.

    FIX: The old aggregation loop had a subtle ordering bug.  row_number() = 1
    is the MOST recent row (ORDER BY datetime DESC), so rn=1 is "current" and
    rn=2 is "previous".  The loop inserted the first-seen row as "current" and
    the second as "prev", which is correct only if the DB returns rn=1 before
    rn=2 for every symbol — not guaranteed by SQL unless an ORDER BY is on the
    outer query.  Added ORDER BY rn ASC to the outer query to make the ordering
    contract explicit.

    FIX: If only one price row exists for a symbol, change stays 0 (correct),
    but prev was left as None and the division guard already handled it.
    No change needed there, but added an explicit zero-division guard comment
    for clarity.
    """
    ranked_subquery = (
        select(
            Stock.symbol,
            Stock.price,
            func.row_number()
            .over(
                partition_by=Stock.symbol,
                order_by=Stock.datetime.desc(),
            )
            .label("rn"),
        )
        .where(
            Stock.symbol.in_(
                select(TokenMap.symbol).where(TokenMap.is_active == True)
            )
        )
        .subquery()
    )

    # FIX: ORDER BY rn ASC guarantees rn=1 (current) arrives before rn=2 (prev)
    query = (
        select(ranked_subquery)
        .where(ranked_subquery.c.rn <= 2)
        .order_by(ranked_subquery.c.symbol, ranked_subquery.c.rn)
    )
    rows = db.execute(query).mappings().all()

    tickers: dict = {}
    for row in rows:
        sym   = row["symbol"]
        price = float(row["price"])

        if row["rn"] == 1:                  # most recent — always current
            tickers[sym] = {"current": price, "prev": None}
        else:                               # rn == 2 — previous
            if sym in tickers:
                tickers[sym]["prev"] = price

    result = {}
    for sym, p in tickers.items():
        change = 0.0
        if p["prev"] and p["prev"] != 0:    # zero-division guard
            change = ((p["current"] - p["prev"]) / p["prev"]) * 100
        result[sym] = {
            "price":  p["current"],
            "change": round(change, 2),
        }

    return result


# ---------------------------------------------------------------------------
# /insight/{symbol}
# ---------------------------------------------------------------------------

@router.get("/insight/{symbol}")
async def get_token_insight(symbol: str, db: Session = Depends(get_db)):
    """
    Returns Lucy's whale-vs-price divergence analysis for a token.

    FIX: analyze_divergence() returns a plain string, not a structured object.
    If symbol doesn't exist in the DB it returns "Neutral (Insufficient Data)"
    rather than raising — that's fine.  Added symbol normalisation to uppercase
    consistent with the rest of the API.
    """
    sym     = symbol.upper()
    insight = analyze_divergence(db, sym)
    return {"symbol": sym, "insight": insight}