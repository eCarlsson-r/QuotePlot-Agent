"""
routers/agent.py — Lucy AI chat router
Bright Data integration map (Discover → Access → Extract → Interact):

  DISCOVER  : brightdata_search_web()          — MCP search_engine finds live web data
  ACCESS    : brightdata_web_unlocker_scrape() — Web Unlocker bypasses blocks/CAPTCHAs
  INTERACT  : brightdata_scrape_dynamic_page() — Scraping Browser drives JS-heavy pages
  EXTRACT   : _brightdata_sources_used()       — Labels which BD pipeline fired per reply
              brightdata_status()              — Live connectivity health-check (cached)
"""

import asyncio
import os
import sys
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor

from dotenv import load_dotenv
from fastapi import APIRouter, Depends
from google import genai
from google.genai import types
from pydantic import BaseModel
from sqlalchemy.orm import Session

from brain import classify_user_intent, get_agent_stats, get_market_prediction
from brightdata_mcp import get_brightdata_market_context, get_brightdata_social_sentiment
from brightdata_utils import (
    get_token_news_serp,
    parse_serp_results,
    scrape_with_scraping_browser,
    scrape_with_web_unlocker,
)
from database import get_db, get_recent_prices
from models import AlternativeData, CompetitivePricing, CorporateRisk, RegulatoryAlert
from utils import extract_symbol, get_fear_and_greed, get_global_movers, mine_investor_behavior

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

# ---------------------------------------------------------------------------
# Bright Data tool functions (sync wrappers — required by Gemini function calling)
#
# Gemini's tool-calling interface expects plain synchronous callables.  We
# bridge to the async implementations via a dedicated ThreadPoolExecutor whose
# threads each own a fresh event loop, avoiding the "loop already running"
# crash that plagued the previous concurrent.futures + asyncio.run() pattern
# on Railway's single-process uvicorn workers.
# ---------------------------------------------------------------------------

_bd_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="bd_tool")


def _run_async_in_thread(coro):
    """Run an async coroutine in a dedicated thread with its own event loop."""
    def _runner():
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    future = _bd_executor.submit(_runner)
    return future.result(timeout=45)


def brightdata_search_web(query: str) -> str:
    """
    [DISCOVER] Search the public web for real-time market data, crypto news,
    and macroeconomic context using Bright Data MCP search_engine.

    Args:
        query: The search query to run.
    """
    try:
        return _run_async_in_thread(get_brightdata_market_context(query))
    except Exception as e:
        return f"[Bright Data Search Error] {e}"


def brightdata_web_unlocker_scrape(url: str) -> str:
    """
    [ACCESS] Scrape the full text of a webpage or news article using Bright
    Data Web Unlocker to bypass bot-detection, CAPTCHAs and geo-blocks.

    Args:
        url: The web URL to scrape.
    """
    try:
        res = _run_async_in_thread(scrape_with_web_unlocker(url))
        return res.get("text", res.get("error", "Web Unlocker returned no content."))
    except Exception as e:
        return f"[Bright Data Web Unlocker Error] {e}"


def brightdata_scrape_dynamic_page(url: str, selector: str = None) -> str:
    """
    [INTERACT] Scrape highly dynamic, JavaScript-heavy websites (DeFi
    dashboards, DexScreener, Uniswap pools) using Bright Data Scraping Browser
    (Playwright / CDP).

    Args:
        url:      The dynamic web URL to navigate.
        selector: Optional CSS selector to wait for before extracting text.
    """
    try:
        res = _run_async_in_thread(scrape_with_scraping_browser(url, selector))
        return res.get("text", res.get("error", "Scraping Browser returned no content."))
    except Exception as e:
        return f"[Bright Data Scraping Browser Error] {e}"


# ---------------------------------------------------------------------------
# Lucy system prompt (defined before LucyAgent so it is always in scope)
# ---------------------------------------------------------------------------

LUCY_SYSTEM_INSTRUCTION = (
    "You are Lucy, a crypto market analyst. Be witty, concise, and data-driven. "
    "When you use live web or alternative data, explicitly cite the pipeline in your reply. "
    "Start those sentences with a short source tag such as "
    "'[Bright Data Web Pipeline Active]' and name the tool used "
    "(SERP API, MCP search_engine, Web Unlocker, or Scraping Browser). "
    "Example: '[Bright Data Web Pipeline Active] Scraped live ecosystem hiring spikes "
    "and pricing indicators for GORK via SERP API. Social sentiment is holding Bullish at 65%.' "
    "Never say you only have vague sentiment if Bright Data context was provided in the prompt. "
    "Use brightdata_search_web, brightdata_web_unlocker_scrape, and brightdata_scrape_dynamic_page "
    "when the user asks for real-time or dynamic web information."
)


# ---------------------------------------------------------------------------
# LucyAgent
# ---------------------------------------------------------------------------

class LucyAgent:
    """
    Wrapper around the Google GenAI chat SDK.

    Key fix: send_message() in google-genai is synchronous.  Calling it
    directly inside an `async def` blocks the uvicorn event loop for the
    entire LLM round-trip (~1-3 s), starving all other requests.  We offload
    it to the same BD thread-pool executor so the event loop stays free.
    """

    _MODEL = "gemini-2.5-flash"   # Single source of truth — no dead model_id field

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        self.client        = genai.Client(api_key=api_key)
        self.chat_sessions: dict = {}

    def get_or_create_session(self, session_id: str):
        if session_id not in self.chat_sessions:
            self.chat_sessions[session_id] = self.client.chats.create(
                model=self._MODEL,
                config=types.GenerateContentConfig(
                    system_instruction=LUCY_SYSTEM_INSTRUCTION,
                    tools=[
                        brightdata_search_web,
                        brightdata_web_unlocker_scrape,
                        brightdata_scrape_dynamic_page,
                    ],
                ),
            )
        return self.chat_sessions[session_id]

    async def generate(self, prompt: str, session_id: str) -> str:
        """Offload the blocking send_message() call to a thread."""
        chat = self.get_or_create_session(session_id)
        response = await asyncio.get_event_loop().run_in_executor(
            _bd_executor,
            lambda: chat.send_message(prompt),
        )
        return response.text

    async def get_narration(
        self, session_id, symbol, sentiment, confidence, insight, behavior, user_query
    ) -> str:
        prompt = (
            f"CONTEXT: {symbol} is {sentiment} ({confidence * 100:.1f}%). "
            f"{insight}. Whales: {behavior}. USER: {user_query}"
        )
        return await self.generate(prompt, session_id)


lucy_brain = LucyAgent()

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router           = APIRouter(prefix="/api/agent", tags=["agent"])
prediction_history = deque(maxlen=100)

# ---------------------------------------------------------------------------
# Bright Data status endpoint — with TTL cache to prevent per-poll handshakes
# ---------------------------------------------------------------------------

_bd_status_cache: dict = {"result": None, "expires_at": 0.0}
_BD_STATUS_TTL = 30.0  # seconds


@router.get("/brightdata-status")
async def brightdata_status():
    """
    Lightweight status for the dashboard connectivity badge.

    Fix: previously opened a full MCP client + get_tools() handshake on every
    dashboard poll (potentially every 5-10 s).  Now cached for 30 s so the BD
    MCP server is not hammered.
    """
    now = time.monotonic()
    if _bd_status_cache["result"] and now < _bd_status_cache["expires_at"]:
        return _bd_status_cache["result"]

    token   = os.getenv("BRIGHTDATA_TOKEN")
    api_key = os.getenv("BRIGHTDATA_API_KEY")
    serp    = os.getenv("BRIGHTDATA_SERP_ZONE")

    result: dict

    if not token and not api_key:
        result = {"connected": False, "label": "Bright Data: Not Configured"}

    elif token:
        try:
            from langchain_mcp_adapters.client import MultiServerMCPClient

            client = MultiServerMCPClient({
                "bright_data": {
                    "url":       f"https://mcp.brightdata.com/mcp?token={token}",
                    "transport": "streamable_http",
                }
            })
            tools = await client.get_tools()
            result = {
                "connected":  bool(tools),
                "label":      "Bright Data MCP Connected" if tools else "Bright Data MCP: No tools",
                "tool_count": len(tools),
            }
        except Exception as exc:
            print(f"⚠️ Bright Data MCP status check: {exc}")
            result = (
                {"connected": True,  "label": "Powered by Bright Data SERP"}
                if api_key and serp
                else {"connected": False, "label": "Bright Data: Connection Error"}
            )

    elif api_key and serp:
        result = {"connected": True, "label": "Powered by Bright Data SERP"}

    else:
        result = {"connected": False, "label": "Bright Data: Connection Error"}

    _bd_status_cache["result"]     = result
    _bd_status_cache["expires_at"] = now + _BD_STATUS_TTL
    return result


# ---------------------------------------------------------------------------
# Source attribution helpers
# ---------------------------------------------------------------------------

def _brightdata_sources_used(
    news_context:     str = "",
    social_sentiment: str = "",
    macro_context:    str = "",
) -> list[str]:
    sources = []
    if news_context:
        sources.append("Bright Data SERP API")
    if social_sentiment and "unavailable" not in social_sentiment.lower():
        sources.append("Bright Data MCP (search_engine)")
    if macro_context and "unavailable" not in macro_context.lower():
        sources.append("Bright Data MCP / SERP macro feed")
    return sources


def _with_brightdata_prefix(reply: str, sources: list[str]) -> str:
    if not sources or not reply:
        return reply
    if reply.strip().startswith("[Bright Data"):
        return reply
    return f"[Bright Data Web Pipeline Active] Pulled live context via {', '.join(sources)}. {reply}"


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    content:    str
    session_id: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/token-stats/{symbol}")
async def fetch_token_stats(symbol: str, db: Session = Depends(get_db)):
    win_rate, total, streak = get_agent_stats(db, symbol)
    return {"win_rate": win_rate, "total_trades": total, "streak": streak}


@router.post("/reply")
async def chat_agent_reply(request: ChatRequest, db: Session = Depends(get_db)):
    intent = classify_user_intent(request.content)

    # ------------------------------------------------------------------
    # Branch 1: Specific token query
    # ------------------------------------------------------------------
    if intent == "market_query":
        symbol = extract_symbol(db, request.content)
        if not symbol:
            return {"reply": "I couldn't identify a token — try mentioning BTC, ETH, or SOL!"}

        prices = get_recent_prices(symbol, db)
        if not prices:
            return {
                "reply":           f"I see you're asking about {symbol}, but I don't have enough data in my memory yet!",
                "prediction_type": "Neutral",
                "probability":     0.5,
            }

        behavior_context = mine_investor_behavior(db, symbol)

        # FIX: was an early-return bare string → now a proper dict so the
        # client always receives a consistent reply/prediction_type/probability shape.
        if behavior_context == "No recent whale activity detected (Insufficient Data)":
            return {
                "reply":           f"⚠️ {symbol}: {behavior_context} — Lucy needs more on-chain data before she can call this one.",
                "prediction_type": "Neutral",
                "probability":     0.5,
            }

        # [DISCOVER] All three Bright Data calls + get_market_prediction run in
        # parallel via gather — previously sequential, adding 3-9s of dead wait
        # time before Gemini even started. gather() fires all four concurrently
        # and returns when the slowest one finishes.
        (
            news_data,
            social_sentiment,
            macro_context,
            (sent, conf, insight),
        ) = await asyncio.gather(
            get_token_news_serp(symbol),                              # SERP news
            get_brightdata_social_sentiment(symbol),                  # MCP social
            get_brightdata_market_context(f"{symbol} macro outlook"), # MCP macro
            asyncio.to_thread(get_market_prediction, db, prices, symbol, behavior_context),
        )

        parsed_news  = parse_serp_results(news_data)
        news_context = ""
        if "error" not in parsed_news and parsed_news.get("organic_results"):
            top_news     = parsed_news["organic_results"][:3]
            news_context = " Recent news: " + "; ".join(n["title"] for n in top_news)

        if news_context:
            insight += news_context
        if social_sentiment and "Macro analysis unavailable" not in social_sentiment:
            insight += f" Social sentiment: {social_sentiment[:200]}..."

        # FIX: macro_context now correctly forwarded so the source badge fires
        sources = _brightdata_sources_used(news_context, social_sentiment, macro_context)
        if sources:
            insight += (
                f"\nBright Data live feeds active ({', '.join(sources)}). "
                "Cite these sources explicitly in your reply."
            )

        try:
            narration = await lucy_brain.get_narration(
                session_id   = request.session_id,
                symbol       = symbol,
                sentiment    = sent,
                confidence   = conf,
                insight      = insight,
                behavior     = behavior_context,
                user_query   = request.content,
            )
            narration = _with_brightdata_prefix(narration, sources)
        except Exception as exc:
            print(f"❌ Lucy narration error: {exc}")
            narration = _with_brightdata_prefix(insight, sources)

        return {
            "reply":           narration,
            "symbol":          symbol,
            "prediction_type": sent,
            "probability":     conf,
            "insight_text":    insight,
        }

    # ------------------------------------------------------------------
    # Branch 2: Global market overview
    # ------------------------------------------------------------------
    elif intent == "global_market_query":
        # FIX: get_fear_and_greed() and get_global_movers() are now async
        # (updated in utils.py). Must be awaited — old code called them as
        # plain functions which would have raised TypeError after the utils rewrite.
        sentiment, movers = await asyncio.gather(
            get_fear_and_greed(),
            get_global_movers(),
        )

        # [DISCOVER] Bright Data MCP — macro context
        macro_context = await get_brightdata_market_context("crypto market trends")
        sources       = _brightdata_sources_used(macro_context=macro_context)

        gainers_str = (
            ", ".join(movers["top_gainers"]) if movers.get("top_gainers") else "None cached"
        )
        source_note = (
            f"\nLive macro context source: {movers.get('source', 'BD Proxy')}. "
            f"F&G source: {sentiment.get('source', 'BD Proxy')}."
        )

        recommendation_prompt = (
            "You are Lucy, an advanced enterprise crypto analyst with native web agency. "
            "The user is asking for general market recommendations, macro summaries, or top movers.\n\n"
            "--- LOCAL DATABASE TELEMETRY ---\n"
            f"Fear & Greed Index: {sentiment['sentiment']} ({sentiment['value']}/100)"
            f"  [{sentiment.get('source', '')}]\n"
            f"Top Movers: {gainers_str}  [{movers.get('source', '')}]\n\n"
            "--- CRITICAL USER INTERFACE ACTIONS ---\n"
            "If you suggest specific tokens or stocks (such as BTC, ETH, SOL, or hot alternatives), "
            "you MUST wrap each ticker inside an interactive HTMX element exactly matching this pattern:\n"
            "'<button class=\"top-mover-btn px-2 py-1 mx-1 bg-blue-600/30 border border-blue-500/50 "
            "rounded text-xs transition-all font-mono\" data-symbol=\"SOL\">SOL</button>'\n\n"
            "This lets the user click your recommended token to update the terminal's visual chart instantly! "
            "If you need real-time data on macro trends, use your brightdata_search_web tool. "
            "Be concise, analytical, witty, and return raw conversational text with embedded markup buttons."
            f"{source_note}"
        )

        try:
            response = await asyncio.get_event_loop().run_in_executor(
                _bd_executor,
                lambda: lucy_brain.get_or_create_session(request.session_id).send_message(
                    f"{recommendation_prompt}\n\nUser Request: {request.content}"
                ),
            )
            reply = _with_brightdata_prefix(response.text, sources)
            return {"reply": reply, "prediction_type": "Neutral", "probability": 0.50}

        except Exception as exc:
            print(f"❌ Global market query error: {exc}")
            fallback = (
                f"[Bright Data Web Pipeline Active] Swapping internal parameters.\n\n"
                f"Global market metrics: **{sentiment['value']}/100** ({sentiment['sentiment']}). "
                f"Top gainers: {gainers_str}."
            )
            return {"reply": fallback, "prediction_type": "Neutral", "probability": 0.50}

    # ------------------------------------------------------------------
    # Branch 3: General chat
    # ------------------------------------------------------------------
    else:
        narration = await lucy_brain.generate(request.content, request.session_id)
        return {"reply": narration}

    # Unreachable but keeps linters happy
    return {"reply": "I'm Lucy! Ask me something like 'How is SOL looking?'"}