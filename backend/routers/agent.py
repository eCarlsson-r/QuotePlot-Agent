import os
from dotenv import load_dotenv
from fastapi import Depends, APIRouter
from collections import deque
from sqlalchemy.orm import Session
from brain import classify_user_intent, get_market_prediction, get_agent_stats # <--- THE NEW BRAIN
from utils import extract_symbol, mine_investor_behavior, get_fear_and_greed, get_global_movers
from database import get_db, get_recent_prices
from pydantic import BaseModel
from google import genai
from google.genai import types

# Load environment variables
load_dotenv()

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
                    system_instruction="You are Lucy. Be witty, concise, and refer to past data."
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
            
            sent, conf, insight = get_market_prediction(db, prices, symbol, behavior_context)

            try :
                narration = await lucy_brain.get_narration(
                    session_id=request.session_id, 
                    symbol=symbol, 
                    sentiment=sent, 
                    confidence=conf, 
                    insight=insight, 
                    behavior=behavior_context,
                    user_query=request.content
                )
            
                return {
                    "reply": narration,
                    "symbol": symbol,
                    "prediction_type": sent,
                    "probability": conf,
                    "insight_text": insight
                }
            except Exception:
                return {
                    "reply": insight,
                    "symbol": symbol,
                    "prediction_type": sent,
                    "probability": conf,
                    "insight_text": insight
                }
    elif intent == "global_market_query":
        sentiment = get_fear_and_greed()
        movers = get_global_movers()

        prompt = f"""
        The user is asking about the general market. 
        Current Sentiment: {sentiment['sentiment']} ({sentiment['value']}/100)
        Top Performers: {', '.join(movers['top_gainers'])}
        
        Provide a concise analyst summary.
        """

        summary = await lucy_brain.generate(prompt, request.session_id)

        return {
            "type": "global_market_update",
            "content": {
                "title": "Global Market Briefing",
                "sentiment": f"{sentiment['sentiment']} ({sentiment['value']}/100)",
                "top_gainers": movers['top_gainers'],
                "summary": summary
            }
        }
    else:
        narration = await lucy_brain.get_narration(
            session_id=request.session_id, 
            user_query=request.content
        )

        return {
            "reply": narration
        }

    return {"reply": "I'm Lucy! Ask me something like 'How is SOL looking?'"}