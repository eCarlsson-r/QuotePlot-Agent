import json
import time
import logging
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Form, Request
from fastapi.concurrency import run_in_threadpool   # single import — duplicate removed
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

from brain import analyze_divergence, get_agent_stats
from database import SessionLocal, get_db
from models import Stock, TokenMap
from routers.agent import ChatRequest, chat_agent_reply

logger = logging.getLogger("uvicorn.error")

# ---------------------------------------------------------------------------
# Ticker cache — module-level, shared across all requests
# ---------------------------------------------------------------------------

_TICKERS_CACHE: dict[str, Any] = {"data": None, "expiry": 0.0}
CACHE_DURATION_SECONDS = 15

router    = APIRouter(tags=["pages"])
_BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(_BASE_DIR / "templates"))
templates.env.enable_async = True


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

def _get_or_set_session_id(request: Request) -> str:
    return request.cookies.get("lucy_session_id") or uuid.uuid4().hex[:12]


def _apply_session_cookie(response: HTMLResponse, request: Request, session_id: str) -> None:
    """Set the session cookie on any response if it is not already present."""
    if not request.cookies.get("lucy_session_id"):
        response.set_cookie(
            "lucy_session_id",
            session_id,
            httponly=True,
            samesite="lax",
            max_age=60 * 60 * 24 * 30,
        )


# ---------------------------------------------------------------------------
# Sync DB helpers (safe to run in threadpool — each opens its own state)
# ---------------------------------------------------------------------------

def _fetch_tickers(db: Session) -> dict[str, Any]:
    """
    Returns { "BTC": {"price": …, "change": …}, … } for the ticker bar.

    FIX 1: Cache was never written. The expiry check always evaluated False
    (expiry stayed 0) and the stale fallback was always None, so every request
    hit the DB regardless. Now writes _TICKERS_CACHE after a successful fetch.

    FIX 2: Window function outer query had no ORDER BY, so rn=2 (previous
    price) could arrive before rn=1 (current), inverting the change sign.
    Now orders by (symbol, rn) and keys off row["rn"] == 1 instead of
    insertion order.
    """
    current_time = time.time()

    if _TICKERS_CACHE["data"] is not None and current_time < _TICKERS_CACHE["expiry"]:
        return _TICKERS_CACHE["data"]

    try:
        active_symbols_query = select(TokenMap.symbol).where(TokenMap.is_active == True)
        active_symbols = db.execute(active_symbols_query).scalars().all()

        if not active_symbols:
            return {}

        ranked_subquery = (
            select(
                Stock.symbol,
                Stock.price,
                func.row_number()
                .over(partition_by=Stock.symbol, order_by=Stock.datetime.desc())
                .label("rn"),
            )
            .where(Stock.symbol.in_(active_symbols))
            .subquery()
        )

        # FIX: ORDER BY guarantees rn=1 (current) always arrives before rn=2 (prev)
        query = (
            select(ranked_subquery)
            .where(ranked_subquery.c.rn <= 2)
            .order_by(ranked_subquery.c.symbol, ranked_subquery.c.rn)
        )
        rows = db.execute(query).mappings().all()

        tickers: dict[str, dict[str, float | None]] = {}
        for row in rows:
            sym   = row["symbol"]
            price = float(row["price"])
            if row["rn"] == 1:              # most recent — always current
                tickers[sym] = {"current": price, "prev": None}
            else:                           # rn == 2 — previous
                if sym in tickers:
                    tickers[sym]["prev"] = price

        result: dict[str, Any] = {}
        for sym, p in tickers.items():
            change = 0.0
            if p["prev"] and p["prev"] != 0:
                change = ((p["current"] - p["prev"]) / p["prev"]) * 100
            result[sym] = {"price": p["current"], "change": round(change, 2)}

        # FIX: write the result into the cache so subsequent calls benefit from it
        _TICKERS_CACHE["data"]   = result
        _TICKERS_CACHE["expiry"] = current_time + CACHE_DURATION_SECONDS
        return result

    except Exception as e:
        if _TICKERS_CACHE["data"] is not None:
            logger.warning(f"⚠️ _fetch_tickers DB error; returning stale cache. ({e})")
            return _TICKERS_CACHE["data"]
        raise


def _fetch_history(db: Session, symbol: str) -> list[dict[str, Any]]:
    # FIX: normalise to uppercase so the helper is safe regardless of call site
    query = sql_text(
        "SELECT price, datetime FROM stocks "
        "WHERE symbol = :s ORDER BY datetime ASC LIMIT 1000"
    )
    rows = db.execute(query, {"s": symbol.upper()}).mappings().all()
    return [
        {"datetime": int(r["datetime"].timestamp() * 1000), "price": float(r["price"])}
        for r in rows
    ]


def _default_insight(db: Session, symbol: str) -> dict[str, Any]:
    try:
        text = analyze_divergence(db, symbol.upper())
        if not isinstance(text, str):
            text = str(text)
        upper = text.upper()
        if "BULLISH" in upper:
            prediction = "Bullish"
        elif "BEARISH" in upper:
            prediction = "Bearish"
        else:
            prediction = "Neutral"
        return {"prediction": prediction, "probability": 0.5, "trend_summary": text}
    except Exception:
        return {"prediction": "Neutral", "probability": 0.0, "trend_summary": ""}


def _fetch_agent_stats(symbol: str) -> tuple[float, int, int]:
    """
    FIX: get_agent_stats() was called via run_in_threadpool(get_agent_stats, db, symbol),
    sharing the route's SQLAlchemy Session across threads. SQLAlchemy Sessions are not
    thread-safe and this can produce DetachedInstanceError or silent stale reads.
    This wrapper opens its own short-lived Session so the threadpool worker is fully
    isolated from the async route's DB state.
    """
    with SessionLocal() as db:
        return get_agent_stats(db, symbol)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    symbol:  str     = "BTC",
    db:      Session = Depends(get_db),
):
    symbol     = symbol.upper()
    session_id = _get_or_set_session_id(request)

    try:
        start = time.time()
        tickers = await run_in_threadpool(_fetch_tickers, db)
        logger.info(f"⏱️ _fetch_tickers:   {time.time() - start:.4f}s")

        start = time.time()
        history = await run_in_threadpool(_fetch_history, db, symbol)
        logger.info(f"⏱️ _fetch_history:   {time.time() - start:.4f}s")

        start = time.time()
        insight = await run_in_threadpool(_default_insight, db, symbol)
        logger.info(f"⏱️ _default_insight: {time.time() - start:.4f}s")

        start = time.time()
        # FIX: uses its own Session — no shared-Session thread-safety issue
        win_rate, total, streak = await run_in_threadpool(_fetch_agent_stats, symbol)
        logger.info(f"⏱️ _fetch_agent_stats: {time.time() - start:.4f}s")

    except Exception as e:
        logger.error(f"❌ Dashboard data error: {e}")
        tickers = {}
        history = []
        insight = {"prediction": "Unavailable", "probability": 0.0, "trend_summary": ""}
        win_rate, total, streak = 0.0, 0, 0

    response = templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "symbol":          symbol,
            "session_id":      session_id,
            "tickers":         tickers,
            "history_json":    json.dumps(history),
            "insight":         insight,
            "insight_json":    json.dumps(insight),
            "stats":           {"win_rate": win_rate, "total_trades": total, "streak": streak},
            "initial_message": f"System initialized. Current analysis for {symbol}: {insight['prediction']}",
        },
    )
    _apply_session_cookie(response, request, session_id)
    return response


@router.get("/partials/ticker-rows", response_class=HTMLResponse)
async def ticker_rows(
    request: Request,
    symbol:  str     = "BTC",
    q:       str     = "",
    db:      Session = Depends(get_db),
):
    symbol  = symbol.upper()
    tickers = await run_in_threadpool(_fetch_tickers, db)

    response = templates.TemplateResponse(
        request,
        "partials/ticker_rows.html",
        {"tickers": tickers, "symbol": symbol, "q": q.strip().upper()},
    )
    return response


@router.post("/partials/chat", response_class=HTMLResponse)
async def chat_partial(
    request: Request,
    content: str     = Form(...),
    symbol:  str     = Form("BTC"),
    db:      Session = Depends(get_db),
):
    symbol       = symbol.upper()
    session_id   = _get_or_set_session_id(request)
    user_content = content.strip()

    if not user_content:
        return HTMLResponse("", status_code=204)

    chat_req = ChatRequest(content=user_content, session_id=session_id)
    try:
        data = await chat_agent_reply(chat_req, db)
    except Exception as exc:
        data = {"reply": f"Error: Could not reach the brain. ({exc})"}

    new_symbol = symbol
    insight: dict[str, Any] = {"prediction": "Neutral", "probability": 0.0}

    # FIX: removed the dead `data.get("type") == "global_market_update"` branch.
    # chat_agent_reply never returns that key — the branch was always skipped.
    # The handler below covers all three intent paths (market_query, global_market_query,
    # general chat) since they all return a "reply" key at minimum.
    reply = data.get("reply", "I'm Lucy! Ask me about a token.")
    messages: list[dict[str, Any]] = [
        {"role": "user",      "content": user_content},
        {"role": "assistant", "content": reply},
    ]

    if data.get("symbol"):
        new_symbol = str(data["symbol"]).upper()

    insight = {
        "prediction":    data.get("prediction_type", "Neutral"),
        "probability":   data.get("probability", 0.0),
        "trend_summary": data.get("insight_text", ""),
    }

    response = templates.TemplateResponse(
        request,
        "partials/chat_exchange.html",
        {
            "messages":    messages,
            "symbol":      new_symbol,
            "insight_json": json.dumps(insight),
            "alert": (
                {
                    "symbol":     new_symbol,
                    "sentiment":  insight["prediction"],
                    "confidence": insight["probability"],
                }
                if insight.get("probability", 0.0) >= 0.9
                else None
            ),
        },
    )
    # FIX: persist the session cookie from POST responses too, so a user whose
    # first interaction is a chat message (not a page load) gets a stable session ID.
    _apply_session_cookie(response, request, session_id)
    return response