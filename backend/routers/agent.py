import joblib
from pathlib import Path
from sklearn.svm import SVC
from sqlalchemy.orm import Session
import sqlalchemy
from database import get_db
from fastapi import Depends, APIRouter, HTTPException
from pydantic import BaseModel
from lucy import text as lucy_text  # Your custom legacy logic

# 1. Define the Router
router = APIRouter(prefix="/api/agent", tags=["agent"])

def classify_intent(user_text):
    text = user_text.lower()
    if any(word in text for word in ["chart", "graph", "probability", "predict"]):
        return "TECHNICAL"
    elif any(word in text for word in ["news", "vibe", "feel", "sentiment"]):
        return "SENTIMENT"
    return "GENERAL"

@router.get("/insight/{symbol}")
async def get_lucy_insight(symbol: str, db: Session = Depends(get_db)):
    # 1. Fetch the last 10 rows for context
    query = sqlalchemy.text("""
        SELECT price, datetime FROM stocks 
        WHERE symbol = :s 
        ORDER BY datetime DESC LIMIT 10
    """)
    rows = db.execute(query, {"s": symbol.upper()}).mappings().all()
    
    if not rows:
        return {"summary": "Not enough data for analysis yet."}

    # 2. Format data for Lucy's brain (example: simplified trend string)
    prices = [float(r['price']) for r in rows]
    trend = "rising" if prices[0] > prices[-1] else "falling"
    
    # 3. Use your legacy 'msgClassifier' or a simple logic bridge
    # For now, we'll simulate her prediction based on the trend
    prediction = "Bullish" if trend == "rising" else "Bearish"

    # Inside get_lucy_insight, replace probability = 0.84 with:
    diff = abs(prices[0] - prices[-1])
    avg = sum(prices) / len(prices)
    # A simple way to get a confidence number between 0.5 and 0.95
    calc_prob = min(0.95, 0.5 + (diff / avg) * 10)
    
    return {
        "symbol": symbol,
        "last_price": prices[0],
        "trend_summary": f"Lucy observes a {trend} trend over the last 10 syncs.",
        "prediction": prediction,
        "probability": calc_prob # Simulated confidence
    }

# 2. Define Request/Response Models
class ChatRequest(BaseModel):
    content: str

class ChatResponse(BaseModel):
    reply: str
    prediction_type: str
    probability: float

# 3. Startup: Load the legacy model once
# Using Path for better compatibility across Windows/Linux
BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "demos/usenet_questions/models/data_questions_pipeline.joblib"
VOCAB_PATH = BASE_DIR / "demos/usenet_questions/models/data_questions_vocab.txt"

try:
    msg_classifier_bundle = joblib.load(MODEL_PATH)
    # Extract the pipeline from our dictionary bundle
    msgClassifier = msg_classifier_bundle['pipeline']
    r = lucy_text.readvocab(VOCAB_PATH)
    vocab, vocabtf, vocabidf = r[0], r[1], r[2]
except FileNotFoundError:
    print(f"❌ ERROR: Lucy AI models not found at {MODEL_PATH}")
    msgClassifier = None

# ... (Imports and Path setup remain the same) ...

# 4. The Chat Endpoint
@router.post("/reply", response_model=ChatResponse)
async def chat_agent_reply(request: ChatRequest, db: Session = Depends(get_db)):
    intent = classify_intent(request.content)
    
    if intent == "TECHNICAL":
        # Lucy triggers the SVC model and amCharts update
        return {"content": "Analyzing technical indicators and SVC probability...", "tool": "chart_update"}
    elif intent == "SENTIMENT":
        # Lucy scans news headlines or social data
        return {"content": "Mining current market sentiment and news cycles...", "tool": "sentiment_scan"}
    
    return {"content": "How can I help with your market research today?"}
    try:
        # 1. Classification Logic (Your SVC Model)
        fv = lucy_text.genfeatureVectorFromString(request.content, vocab, vocabidf)
        prediction = msgClassifier.predict([fv])[0]
        probs = msgClassifier.predict_proba([fv])[0]
        
        is_open = int(prediction) == 1
        p_type = "Open question" if is_open else "Closed question"
        class_confidence = float(probs[1] if is_open else probs[0])

        # 2. Market Logic (The Lucy Insight Bridge)
        content_lower = request.content.lower()
        # Simple keyword detection
        target_symbol = "BTC" # Default
        if "eth" in content_lower or "ethereum" in content_lower:
            target_symbol = "ETH"
        elif "sol" in content_lower or "solana" in content_lower:
            target_symbol = "SOL"

        # Now fetch the real context using your existing function
        market_info = await get_lucy_insight(target_symbol, db)
        
        # 3. Formulate the "Smart" Reply
        if is_open:
            custom_reply = (
                f"I've classified this as an {p_type.lower()}. "
                f"Looking at {target_symbol}, {market_info['trend_summary']} "
                f"The current sentiment is {market_info['prediction']}."
            )
        else:
            custom_reply = f"I've noted your comment. My current analysis for {target_symbol} remains {market_info['prediction']}."

        # Add the confidence warning if classification is shaky
        if class_confidence < 0.65:
            custom_reply += " (I'm leaning towards this interpretation, but clarify if I'm off!)"

        return {
            "reply": custom_reply,
            "prediction_type": p_type,
            "probability": market_info['probability'] # Drive the gauge with market probability!
        }
        
    except Exception as e:
        print(f"Prediction Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))