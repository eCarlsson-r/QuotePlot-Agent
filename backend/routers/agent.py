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
    
    return {
        "symbol": symbol,
        "last_price": prices[0],
        "trend_summary": f"Lucy observes a {trend} trend over the last 10 syncs.",
        "prediction": prediction,
        "probability": 0.84 # Simulated confidence
    }

# 2. Define Request/Response Models
class ChatRequest(BaseModel):
    content: str
    wallet_address: str  # Web3 Ready

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
async def chat_agent_reply(request: ChatRequest):
    if msgClassifier is None:
        raise HTTPException(status_code=500, detail="AI Model not loaded on server.")
        
    try:
        # 1. Generate feature vector from the message string using Lucy's logic
        fv = lucy_text.genfeatureVectorFromString(request.content, vocab, vocabidf)
        
        # 2. Perform prediction using the Pipeline (Normalizer + SVC)
        # We wrap [fv] because Scikit-Learn expects a list of samples
        prediction = msgClassifier.predict([fv])[0]
        probs = msgClassifier.predict_proba([fv])[0]
        
        # 3. Determine the "Prediction Type" based on your model's classes
        # Class 1 = Open Question, Class 0 = Closed/Other (based on your eval report)
        is_open = int(prediction) == 1
        p_type = "Open question" if is_open else "Closed question"
        
        # 4. Get the confidence for the specific predicted class
        # probs[1] is confidence for Class 1, probs[0] for Class 0
        confidence = float(probs[1] if is_open else probs[0])
        
        # 5. Add a "Low Confidence" check for the 0.56 precision area
        custom_reply = f"Lucy classifies this as an {p_type.lower()}."
        if confidence < 0.65:
            custom_reply += " (Note: I am leaning toward this, but I'm not entirely certain.)"
        
        return {
            "reply": custom_reply,
            "prediction_type": p_type,
            "probability": confidence
        }
        
    except Exception as e:
        # Log the error for debugging
        print(f"Prediction Error: {e}")
        raise HTTPException(status_code=500, detail=f"Lucy encountered an error: {str(e)}")