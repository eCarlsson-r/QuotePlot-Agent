import joblib
import numpy as np
from pathlib import Path
from sklearn.pipeline import Pipeline
from models import PredictionLog
from lucy import text as lucy_text  # Your custom legacy logic

# Load the model once
BASE_DIR = Path(__file__).resolve().parent

# --- 1. LOAD THE TEXT CLASSIFIER (The Social Lobe) ---
TEXT_MODEL_PATH = BASE_DIR / "demos/usenet_questions/models/data_questions_pipeline.joblib"
VOCAB_PATH = BASE_DIR / "demos/usenet_questions/models/data_questions_vocab.txt"

try:
    msg_bundle = joblib.load(TEXT_MODEL_PATH)
    msg_classifier = msg_bundle['pipeline']
    # Load the vocabulary translator
    v_data = lucy_text.readvocab(VOCAB_PATH)
    vocab, vocabtf, vocabidf = v_data[0], v_data[1], v_data[2]
except Exception as e:
    print(f"⚠️ Social Lobe failed to load: {e}")
    msg_classifier = None

# --- 2. LOAD THE MARKET BRAIN (The Analytical Lobe) ---
MARKET_MODEL_PATH = BASE_DIR / "models/market_sentiment_svc.joblib"

try:
    market_bundle = joblib.load(MARKET_MODEL_PATH)
    market_brain = market_bundle["model"] if isinstance(market_bundle, dict) else market_bundle
except Exception as e:
    print(f"⚠️ Market Brain failed to load: {e}")
    market_brain = None

# --- EXPORTED FUNCTIONS ---

def classify_user_intent(message: str):
    INTENT_KEYWORDS = {
        "MARKET": ["price", "chart", "analysis", "technical", "prediction", "indicators", "target", "news", "opinion", "sentiment", "feeling", "social", "twitter", "hype"],
        "GREETING": ["hello", "hi", "hey", "lucy", "morning", "help"]
    }
    text_lower = message.lower()

    if any(kw in text_lower for kw in INTENT_KEYWORDS["MARKET"]):
        return "market_query"
    
    if any(kw in text_lower for kw in INTENT_KEYWORDS["GREETING"]):
        return "general_chat"

    """Translates text into an intent (Market vs General)."""
    if msg_classifier:
        try:
            fv = lucy_text.genfeatureVectorFromString(message, vocab, vocabidf)
            prediction = msg_classifier.predict([fv])[0]
            return "market_query" if int(prediction) == 1 else "general_chat"
        except Exception as e:
            print(f"ML Classification Error: {e}")
    return "general_chat" # Default fallback

def prepare_market_features(prices: list):
    """Normalizes price data into a feature vector."""
    prices_array = np.array(prices).reshape(-1, 1)
    mean = np.mean(prices_array)
    std = np.std(prices_array) if np.std(prices_array) > 0 else 1
    
    return ((prices_array - mean) / std).flatten()

def get_market_prediction(price_data, sentiment_text="Neutral"):
    try:
        # 1. PRICE MINING (for 'Market Trend' & 'Asset Pricing')
        # We calculate the delta instead of passing the raw array to the text model
        price_delta = ((price_data[-1] - price_data[0]) / price_data[0]) * 100
        
        # 2. SENTIMENT MINING (for 'Market Sentiment' & 'Investor Behaviour')
        # We ensure sentiment_text is a string for the TfidfVectorizer
        # market_brain is your SVC model
        sentiment_signal = market_brain.predict([str(sentiment_text)])[0]

        # 3. COMPOSITE ANALYSIS
        # Lucy combines numbers + text to give the "Correct Information"
        if price_delta > 0.5 and sentiment_signal == "Bullish":
            confidence = 0.92
            insight = "Strong accumulation detected alongside positive price action."
        else:
            confidence = 0.65
            insight = "Mixed signals: Market mining shows divergence."

        return sentiment_signal, confidence, insight

    except Exception as e:
        print(f"Lucy Brain Error: {e}")
        return "Neutral", 0.0, "System re-calibrating mining parameters."

def get_agent_stats(db, symbol):
    # Only count predictions where we actually checked the result
    verified_query = db.query(PredictionLog).filter(
        PredictionLog.symbol == symbol,
        PredictionLog.was_evaluated == True
    )
    
    total_trades = verified_query.count()
    wins = verified_query.filter(PredictionLog.was_correct == True).count()
    streak = get_streak(db, symbol)
    
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    return round(win_rate, 2), total_trades, streak

def get_streak(db, symbol):
    # Get the last 10 evaluated predictions, newest first
    recent = db.query(PredictionLog).filter(
        PredictionLog.symbol == symbol,
        PredictionLog.was_evaluated == True
    ).order_by(PredictionLog.timestamp.desc()).limit(10).all()

    streak = 0
    if not recent: return 0
    
    first_result = recent[0].was_correct
    for p in recent:
        if p.was_correct == first_result:
            streak += 1
        else:
            break
    return streak if first_result else -streak # Positive for win streak, negative for loss