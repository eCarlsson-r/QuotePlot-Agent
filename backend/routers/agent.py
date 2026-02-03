import time
from fastapi import Depends, APIRouter
from collections import deque
from sqlalchemy.orm import Session
from brain import classify_user_intent, get_market_prediction # <--- THE NEW BRAIN
from utils import extract_symbol
from database import get_db, get_recent_prices
from pydantic import BaseModel

# 1. Define the Router
router = APIRouter(prefix="/api/agent", tags=["agent"])
prediction_history = deque(maxlen=100)

# 2. Define Request/Response Models
class ChatRequest(BaseModel):
    content: str

class ChatResponse(BaseModel):
    reply: str
    prediction_type: str
    probability: float

@router.get("/stats")
async def get_agent_stats():
    # Filter only the predictions that have been "verified" (success is True or False)
    verified = [p for p in prediction_history if p['success'] is not None]
    
    if not verified:
        return {"win_rate": 0, "total_trades": 0, "avg_confidence": 0, "status": "Calculating..."}
    
    wins = len([p for p in verified if p['success']])
    total = len(verified)
    
    return {
        "win_rate": round((wins / total) * 100, 2),
        "total_trades": total,
        "avg_confidence": round(sum(p['confidence'] for p in verified) / total, 4),
        "history": list(prediction_history)[-10:] # Return last 10 for the UI
    }

# This function would be called inside your /reply endpoint 
# whenever Lucy makes a market prediction
def log_prediction(symbol: str, current_price: float, prediction: str, confidence: float):
    prediction_history.append({
        "timestamp": time.time(),
        "symbol": symbol,
        "price_at_start": current_price,
        "prediction": prediction, # "Bullish" or "Bearish"
        "confidence": confidence,
        "success": None # Will be updated later
    })

async def verify_predictions(current_market_prices: dict):
    """
    Compares historical predictions against current market prices.
    current_market_prices: {"BTC": 95000, "ETH": 2700, ...}
    """
    now = time.time()
    for p in prediction_history:
        # Check predictions made more than 5 minutes ago that aren't verified yet
        if p['success'] is None and (now - p['timestamp']) > 300:
            current_p = current_market_prices.get(p['symbol'])
            if not current_p: continue

            if p['prediction'] == "Bullish":
                p['success'] = current_p > p['price_at_start']
            else:
                p['success'] = current_p < p['price_at_start']

@router.post("/reply")
async def chat_agent_reply(request: ChatRequest, db: Session = Depends(get_db)):
    # Step 1: What is the user talking about?
    intent = classify_user_intent(request.content)
    
    if intent == "market_query":
        # Step 2: Analyze the specific token (e.g., BTC)
        symbol = extract_symbol(request.content)
        
        prices = get_recent_prices(symbol, db)
        
        if not prices:
            return {"reply": f"I see you're asking about {symbol}, but I don't have enough data in my memory yet!"}

        sent, conf = get_market_prediction(prices)
        return {
            "reply": f"Scanning the markets for {symbol}... I'm {conf*100:.1f}% confident we're looking at a {sent} trend.",
            "symbol": symbol
        }
    
    return {"reply": "I'm Lucy! Ask me something like 'How is SOL looking?'"}