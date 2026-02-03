import joblib
import numpy as np
from pathlib import Path
from sklearn.pipeline import Pipeline
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

def get_market_prediction(prices: list):
    """Logic shared by background tasks and the Chat API."""
    if not market_brain or len(prices) < 10:
        # Fallback simple logic
        is_bullish = prices[-1] > prices[0]
        return ("Bullish" if is_bullish else "Bearish"), 0.5
    
    fv = prepare_market_features(prices[-10:])
    prediction = market_brain.predict([fv])[0]
    probs = market_brain.predict_proba([fv])[0]

    sentiment = "BULLISH" if prediction == 1 else "BEARISH"
    return sentiment, max(probs)