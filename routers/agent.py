import os
import sys
from dotenv import load_dotenv
from fastapi import Depends, APIRouter
from collections import deque
from sqlalchemy.orm import Session
from brain import (
    classify_user_intent, 
    get_market_prediction, 
    get_agent_stats,
    generate_earnings_intelligence,
    generate_sector_intelligence
)
from utils import extract_symbol, mine_investor_behavior, get_fear_and_greed, get_global_movers
from database import get_db, get_recent_prices
from models import AlternativeData, RegulatoryAlert, CompetitivePricing, CorporateRisk
from pydantic import BaseModel
from google import genai
from google.genai import types
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from brightdata_mcp import get_brightdata_market_context, get_brightdata_social_sentiment
from brightdata_utils import get_token_news_serp, parse_serp_results, scrape_with_web_unlocker, scrape_with_scraping_browser

# Load environment variables
load_dotenv()

def brightdata_search_web(query: str) -> str:
    """
    Search the public web for real-time market data, crypto news, and macroeconomic context using Bright Data search tools.
    
    Args:
        query: The search query to run.
    """
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    if loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(lambda: asyncio.run(get_brightdata_market_context(query)))
            return future.result()
    else:
        return loop.run_until_complete(get_brightdata_market_context(query))

def brightdata_web_unlocker_scrape(url: str) -> str:
    """
    Scrape the full text of a webpage or news article using Bright Data Web Unlocker to bypass blocks and CAPTCHAs.
    
    Args:
        url: The web URL to scrape.
    """
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    from brightdata_utils import scrape_with_web_unlocker
    if loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(lambda: asyncio.run(scrape_with_web_unlocker(url)))
            res = future.result()
    else:
        res = loop.run_until_complete(scrape_with_web_unlocker(url))
        
    return res.get("text", res.get("error", "Failed to scrape"))

def brightdata_scrape_dynamic_page(url: str, selector: str = None) -> str:
    """
    Scrape highly dynamic, Javascript-heavy websites (like DeFi dashboards, DexScreener, Uniswap pools) using Bright Data Scraping Browser.
    
    Args:
        url: The dynamic web URL to scrape.
        selector: Optional CSS selector to wait for before extracting text.
    """
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    from brightdata_utils import scrape_with_scraping_browser
    if loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(lambda: asyncio.run(scrape_with_scraping_browser(url, selector)))
            res = future.result()
    else:
        res = loop.run_until_complete(scrape_with_scraping_browser(url, selector))
        
    return res.get("text", res.get("error", "Failed to scrape dynamic page"))


class LucyAgent:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.model_id = "gemini-3.0-flash"
        self.chat_sessions = {}

    def get_or_create_session(self, session_id: str):
        if session_id not in self.chat_sessions:
            # Create a fresh session with Lucy's personality
            self.chat_sessions[session_id] = self.client.chats.create(
                model="gemini-2.5-flash",
                config=types.GenerateContentConfig(
                    system_instruction=LUCY_SYSTEM_INSTRUCTION,
                    tools=[brightdata_search_web, brightdata_web_unlocker_scrape, brightdata_scrape_dynamic_page]
                )
            )
        return self.chat_sessions[session_id]


    async def get_narration(self, session_id, symbol, sentiment, confidence, insight, behavior, user_query):
        full_prompt = f"CONTEXT: {symbol} is {sentiment} ({confidence*100}%). {insight}. Whales: {behavior}. USER: {user_query}"
        
        # 3. Use send_message (this automatically updates the history/Interaction IDs internally)
        return await self.generate(full_prompt, session_id)
    
    async def generate(self, prompt, session_id):
        chat = self.get_or_create_session(session_id)
        response = chat.send_message(prompt)
        return response.text

# Initialize once to reuse the connection
lucy_brain = LucyAgent()

# 1. Define the Router
router = APIRouter(prefix="/api/agent", tags=["agent"])
prediction_history = deque(maxlen=100)

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


def _brightdata_sources_used(
    news_context: str = "",
    social_sentiment: str = "",
    macro_context: str = "",
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
    tools = ", ".join(sources)
    return f"[Bright Data Web Pipeline Active] Pulled live context via {tools}. {reply}"


@router.get("/brightdata-status")
async def brightdata_status():
    """Lightweight status for the dashboard connectivity badge."""
    token = os.getenv("BRIGHTDATA_TOKEN")
    api_key = os.getenv("BRIGHTDATA_API_KEY")
    serp = os.getenv("BRIGHTDATA_SERP_ZONE")

    if not token and not api_key:
        return {
            "connected": False,
            "label": "Bright Data: Not Configured",
        }

    if token:
        try:
            from langchain_mcp_adapters.client import MultiServerMCPClient

            client = MultiServerMCPClient({
                "bright_data": {
                    "url": f"https://mcp.brightdata.com/mcp?token={token}",
                    "transport": "streamable_http",
                }
            })
            tools = await client.get_tools()
            if tools:
                return {
                    "connected": True,
                    "label": "Bright Data MCP Connected",
                    "tool_count": len(tools),
                }
        except Exception as exc:
            print(f"⚠️ Bright Data status check: {exc}")

    if api_key and serp:
        return {
            "connected": True,
            "label": "Powered by Bright Data SERP",
        }

    return {
        "connected": False,
        "label": "Bright Data: Connection Error",
    }

# 2. Define Request/Response Models
class ChatRequest(BaseModel):
    content: str
    session_id: str

class ChatResponse(BaseModel):
    reply: str
    prediction_type: str
    probability: float

@router.get("/token-stats/{symbol}")
async def fetch_token_stats(symbol: str, db: Session = Depends(get_db)):
    win_rate, total, streak = get_agent_stats(db, symbol)
    return {
        "win_rate": win_rate,
        "total_trades": total,
        "streak": streak
    }

@router.post("/reply")
async def chat_agent_reply(request: ChatRequest, db: Session = Depends(get_db)):
    # Step 1: What is the user talking about?
    intent = classify_user_intent(request.content)
    
    if intent == "market_query":
        # Step 2: Analyze the specific token (e.g., BTC)
        symbol = extract_symbol(db, request.content)

        if (symbol):
            prices = get_recent_prices(symbol, db)
            
            if not prices:
                return {"reply": f"I see you're asking about {symbol}, but I don't have enough data in my memory yet!"}
            
            behavior_context = mine_investor_behavior(db, symbol)
            if (behavior_context == "No recent whale activity detected (Insufficient Data)"):
                return {"reply": behavior_context}
            
            # Step 2.5: Fetch real-time news using Bright Data SERP API
            news_data = await get_token_news_serp(symbol)
            parsed_news = parse_serp_results(news_data)
            
            # Add news context to the insight if available
            news_context = ""
            if "error" not in parsed_news and parsed_news.get("organic_results"):
                top_news = parsed_news["organic_results"][:3]  # Get top 3 results
                news_context = " Recent news: " + "; ".join([f"{n['title']}" for n in top_news])
            
            # Step 2.6: Fetch social sentiment using Bright Data MCP
            social_sentiment = await get_brightdata_social_sentiment(symbol)
            
            sent, conf, insight = get_market_prediction(db, prices, symbol, behavior_context)
            
            # Enhance insight with news and social context
            if news_context:
                insight += news_context
            if social_sentiment and "Macro analysis unavailable" not in social_sentiment:
                insight += f" Social sentiment: {social_sentiment[:200]}..."

            sources = _brightdata_sources_used(news_context, social_sentiment)
            bd_note = ""
            if sources:
                bd_note = (
                    f"\nBright Data live feeds active ({', '.join(sources)}). "
                    "Cite these sources explicitly in your reply."
                )

            try:
                narration = await lucy_brain.get_narration(
                    session_id=request.session_id,
                    symbol=symbol,
                    sentiment=sent,
                    confidence=conf,
                    insight=insight + bd_note,
                    behavior=behavior_context,
                    user_query=request.content,
                )
                narration = _with_brightdata_prefix(narration, sources)

                return {
                    "reply": narration,
                    "symbol": symbol,
                    "prediction_type": sent,
                    "probability": conf,
                    "insight_text": insight,
                }
            except Exception:
                fallback = _with_brightdata_prefix(insight, sources)
                return {
                    "reply": fallback,
                    "symbol": symbol,
                    "prediction_type": sent,
                    "probability": conf,
                    "insight_text": insight,
                }
    elif intent == "global_market_query":
        sentiment = get_fear_and_greed()
        movers = get_global_movers()
        
        # Fetch macro context using Bright Data MCP
        macro_context = await get_brightdata_market_context("crypto market trends")

        recommendation_prompt = (
            f"You are Lucy, an advanced enterprise crypto analyst with native web agency. "
            f"The user is asking for general market recommendations, macro summaries, or top movers.\n\n"
            f"--- LOCAL DATABASE TELEMETRY ---\n"
            f"Fear & Greed Index: {sentiment['sentiment']} ({sentiment['value']}/100)\n"
            f"Database Top Movers: {', '.join(movers['top_gainers']) if movers.get('top_gainers') else 'None cached'}\n\n"
            f"--- CRITICAL USER INTERFACE ACTIONS ---\n"
            f"If you suggest specific tokens or stocks (such as BTC, ETH, SOL, or hot alternatives), you MUST wrap "
            f"each ticker inside an interactive HTMX element exactly matching this markup pattern:\n"
            f"'<button class=\"top-mover-btn px-2 py-1 mx-1 bg-blue-600/30 border border-blue-500/50 rounded text-xs transition-all font-mono\" data-symbol=\"SOL\">SOL</button>'\n\n"
            f"This lets the user click your recommended token to update the terminal's visual chart canvas instantly! "
            f"If you need real-time data on macro trends, use your brightdata_search_web tool. "
            f"Be concise, analytical, witty, and return raw conversational text with embedded markup buttons."
        )

        try:
            # Pull the active persistent stateful session via the GenAI SDK helper
            chat_session = lucy_brain.get_or_create_session(request.session_id)
            
            # Send the request directly through Gemini's chat stream
            response = chat_session.send_message(
                f"{recommendation_prompt}\n\nUser Request: {request.content}"
            )
            
            # Return the response text directly as the message body content 
            return {
                "reply": response.text,
                "prediction_type": "Neutral",
                "probability": 0.50
            }
            
        except Exception as exc:
            print(f"❌ Error during recommendation processing: {exc}")
            fallback_message = (
                f"[Bright Data Web Pipeline Active] Swapping internal parameters.\n\n"
                f"Global market metrics indicate a position score of **{sentiment['value']}/100** ({sentiment['sentiment']}). "
                f"Top gainers currently include: {', '.join(movers['top_gainers'])}."
            )
            return {
                "reply": fallback_message,
                "prediction_type": "Neutral",
                "probability": 0.50
            }
    else:
        narration = await lucy_brain.generate(
            request.content,
            request.session_id,
        )

        return {
            "reply": narration
        }

    return {"reply": "I'm Lucy! Ask me something like 'How is SOL looking?'"}