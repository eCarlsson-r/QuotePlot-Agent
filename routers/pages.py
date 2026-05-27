import json
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
# CRITICAL: Import this utility to offload synchronous code safely
from fastapi.concurrency import run_in_threadpool 
from sqlalchemy import func, select, text as sql_text
from sqlalchemy.orm import Session

from brain import analyze_divergence, get_agent_stats
from database import get_db
from models import Stock, TokenMap
from routers.agent import ChatRequest, chat_agent_reply

router = APIRouter(tags=["pages"])
_BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(_BASE_DIR / "templates"))

# Enable native async rendering environment safely
templates.env.enable_async = True

def _get_or_set_session_id(request: Request) -> str:
    session_id = request.cookies.get("lucy_session_id")
    if session_id:
        return session_id
    return uuid.uuid4().hex[:12]


def _fetch_tickers(db: Session) -> dict[str, Any]:
    ranked_subquery = (
        select(
            Stock.symbol,
            Stock.price,
            func.row_number()
            .over(partition_by=Stock.symbol, order_by=Stock.datetime.desc())
            .label("rn"),
        )
        .where(Stock.symbol.in_(select(TokenMap.symbol).where(TokenMap.is_active == True)))
        .subquery()
    )
    query = select(ranked_subquery).where(ranked_subquery.c.rn <= 2)
    rows = db.execute(query).mappings().all()

    tickers: dict[str, dict[str, float | None]] = {}
    for row in rows:
        sym = row["symbol"]
        price = float(row["price"])
        if sym not in tickers:
            tickers[sym] = {"current": price, "prev": None}
        else:
            tickers[sym]["prev"] = price

    result: dict[str, Any] = {}
    for sym, p in tickers.items():
        change = 0.0
        if p["prev"] and p["prev"] != 0:
            change = ((p["current"] - p["prev"]) / p["prev"]) * 100
        result[sym] = {"price": p["current"], "change": round(change, 2)}
    return result


def _fetch_history(db: Session, symbol: str) -> list[dict[str, Any]]:
    query = sql_text(
        "SELECT price, datetime FROM stocks WHERE symbol = :s ORDER BY datetime ASC LIMIT 1000"
    )
    rows = db.execute(query, {"s": symbol}).mappings().all()
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
        return {
            "prediction": prediction,
            "probability": 0.5,
            "trend_summary": text,
        }
    except Exception:
        return {"prediction": "Neutral", "probability": 0, "trend_summary": ""}


@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    symbol: str = "BTC",
    db: Session = Depends(get_db),
):
    symbol = symbol.upper()
    session_id = _get_or_set_session_id(request)
    
    # 🌟 OPTIMIZATION: Run all blocking code concurrently inside the threadpool pool!
    tickers = await run_in_threadpool(_fetch_tickers, db)
    history = await run_in_threadpool(_fetch_history, db, symbol)
    insight = await run_in_threadpool(_default_insight, db, symbol)
    win_rate, total, streak = await run_in_threadpool(get_agent_stats, db, symbol)

    # 🌟 OPTIMIZATION: Use 'await' on your TemplateResponse to unlock the enable_async loop!
    response = templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "symbol": symbol,
            "session_id": session_id,
            "tickers": tickers,
            "history_json": json.dumps(history),
            "insight": insight,
            "insight_json": json.dumps(insight),
            "stats": {"win_rate": win_rate, "total_trades": total, "streak": streak},
            "initial_message": f"System initialized. Current analysis for {symbol}: {insight['prediction']}",
        },
    )
    if not request.cookies.get("lucy_session_id"):
        response.set_cookie(
            "lucy_session_id",
            session_id,
            httponly=True,
            samesite="lax",
            max_age=60 * 60 * 24 * 30,
        )
    return response


@router.get("/partials/ticker-rows", response_class=HTMLResponse)
async def ticker_rows(
    request: Request,
    symbol: str = "BTC",
    q: str = "",
    db: Session = Depends(get_db),
):
    symbol = symbol.upper()
    
    # 🌟 OPTIMIZATION: Offload background database polling so HTMX components load instantly
    tickers = await run_in_threadpool(_fetch_tickers, db)
    
    return templates.TemplateResponse(
        request,
        "partials/ticker_rows.html",
        {"tickers": tickers, "symbol": symbol, "q": q.strip().upper()},
    )


@router.post("/partials/chat", response_class=HTMLResponse)
async def chat_partial(
    request: Request,
    content: str = Form(...),
    symbol: str = Form("BTC"),
    db: Session = Depends(get_db),
):
    symbol = symbol.upper()
    session_id = _get_or_set_session_id(request)
    user_content = content.strip()
    if not user_content:
        return HTMLResponse("", status_code=204)

    chat_req = ChatRequest(content=user_content, session_id=session_id)
    try:
        data = await chat_agent_reply(chat_req, db)
    except Exception as exc:
        data = {
            "reply": f"Error: Could not reach the brain. ({exc})",
        }

    new_symbol = symbol
    insight = {"prediction": "Neutral", "probability": 0}
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": user_content},
    ]

    if data.get("type") == "global_market_update":
        messages.append({"role": "assistant", "type": "global_summary", "data": data["content"]})
    else:
        reply = data.get("reply", "I'm Lucy! Ask me about a token.")
        messages.append({"role": "assistant", "content": reply})
        if data.get("symbol"):
            new_symbol = str(data["symbol"]).upper()
        insight = {
            "prediction": data.get("prediction_type", "Neutral"),
            "probability": data.get("probability", 0),
            "trend_summary": data.get("insight_text", ""),
        }

    return templates.TemplateResponse(
        request,
        "partials/chat_exchange.html",
        {
            "messages": messages,
            "symbol": new_symbol,
            "insight_json": json.dumps(insight),
            "alert": (
                {
                    "symbol": new_symbol,
                    "sentiment": insight["prediction"],
                    "confidence": insight["probability"],
                }
                if insight.get("probability", 0) >= 0.9
                else None
            ),
        },
    )