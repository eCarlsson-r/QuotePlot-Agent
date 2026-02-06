import joblib
import numpy as np
from pathlib import Path
from sklearn.pipeline import Pipeline
from models import InvestorBehavior, PredictionLog, Stock
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
        "GREETING": ["hello", "hi", "hey", "lucy", "morning", "help"],
        "GLOBAL_KEYWORDS": ["market", "everything", "all stocks", "overall", "crypto world"]
    }
    text_lower = message.lower()

    if any(kw in text_lower for kw in INTENT_KEYWORDS["MARKET"]):
        return "market_query"
    
    if any(kw in text_lower for kw in INTENT_KEYWORDS["GREETING"]):
        return "general_chat"
    
    if any(kw in text_lower for kw in INTENT_KEYWORDS["GLOBAL_KEYWORDS"]):
        return "global_market_query"

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

def get_market_prediction(db, price_data, symbol, sentiment_text="Neutral"):
    try:
        # 1. Get the Math-based Divergence Analysis first
        # This tells us exactly WHAT the whales are doing vs Price
        divergence_report = analyze_divergence(db, symbol)
        
        # 2. Run your SVC Model (The "Social Lobe")
        # This tells us the "Vibe" of the market sentiment
        sentiment_signal = market_brain.predict([str(sentiment_text)])[0]

        # 3. COMPOSITE ANALYSIS (The Decision)
        price_delta = ((price_data[-1].price - price_data[0].price) / price_data[0].price) * 100
        insight = divergence_report 
        
        # Adjust confidence based on whether the Model and the Divergence agree
        if "CONFIRMATION" in divergence_report and sentiment_signal == "Bullish":
            confidence = 0.98  # Extremely high confidence
        elif "DIVERGENCE" in divergence_report:
            confidence = 0.85  # High confidence that something is wrong
        else:
            confidence = 0.65

        if price_delta > 2.0 and "CONFIRMATION" in divergence_report:
            # This is the "Strong Buy" you had before, but now backed by whale data
            insight = "Healthy rally: Price delta is positive and confirmed by whale accumulation."
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

# market.py or analysis.py
from sqlalchemy import func
from datetime import datetime, timedelta

def analyze_divergence(db, symbol: str):
    """
    Compares the last 24h Price Delta with the last 24h Whale Net Flow.
    Returns a sentiment signal for Lucy's brain.
    """
    one_day_ago = datetime.now() - timedelta(hours=24)

    # 1. Calculate Price Delta
    recent_prices = db.query(Stock).filter(Stock.symbol == symbol, Stock.datetime >= one_day_ago)\
                      .order_by(Stock.datetime.asc()).all()
    
    if len(recent_prices) < 2: return "Neutral (Insufficient Data)"
    
    price_start = float(recent_prices[0].price)
    price_end = float(recent_prices[-1].price)
    price_delta_pct = ((price_end - price_start) / price_start) * 100

    # 2. Calculate Whale Net Flow (Accumulation vs Distribution)
    inflow = db.query(func.sum(InvestorBehavior.volume)).filter(
        InvestorBehavior.symbol == symbol,
        InvestorBehavior.flow_type == "Cold Storage", # Bullish move
        InvestorBehavior.timestamp >= one_day_ago
    ).scalar() or 0

    outflow = db.query(func.sum(InvestorBehavior.volume)).filter(
        InvestorBehavior.symbol == symbol,
        InvestorBehavior.flow_type == "Exchange Inflow", # Bearish move
        InvestorBehavior.timestamp >= one_day_ago
    ).scalar() or 0

    net_flow = inflow - outflow

    # 3. DIVERGENCE LOGIC
    # CASE A: Bearish Divergence (Price Up, Whales Selling)
    if price_delta_pct > 3.0 and net_flow < 0:
        return "⚠️ BEARISH DIVERGENCE: Price is pumping, but whales are exiting. Potential trap."

    # CASE B: Bullish Divergence (Price Down, Whales Buying)
    elif price_delta_pct < -3.0 and net_flow > 0:
        return "🚀 BULLISH DIVERGENCE: Price is dipping, but whales are accumulating. Strong buy signal."

    # CASE C: Confirmation (Both moving together)
    elif price_delta_pct > 0 and net_flow > 0:
        return "✅ BULLISH CONFIRMATION: Market and whales are aligned in accumulation."

    return "Neutral: Market noise."# market.py or analysis.py
from sqlalchemy import func
from datetime import datetime, timedelta

def analyze_divergence(db, symbol: str):
    """
    Compares the last 24h Price Delta with the last 24h Whale Net Flow.
    Returns a sentiment signal for Lucy's brain.
    """
    one_day_ago = datetime.now() - timedelta(hours=24)

    # 1. Calculate Price Delta
    recent_prices = db.query(Stock).filter(Stock.symbol == symbol, Stock.datetime >= one_day_ago)\
                      .order_by(Stock.datetime.asc()).all()
    
    if len(recent_prices) < 2: return "Neutral (Insufficient Data)"
    
    price_start = float(recent_prices[0].price)
    price_end = float(recent_prices[-1].price)
    price_delta_pct = ((price_end - price_start) / price_start) * 100

    # 2. Calculate Whale Net Flow (Accumulation vs Distribution)
    inflow = db.query(func.sum(InvestorBehavior.volume)).filter(
        InvestorBehavior.symbol == symbol,
        InvestorBehavior.flow_type == "Cold Storage", # Bullish move
        InvestorBehavior.timestamp >= one_day_ago
    ).scalar() or 0

    outflow = db.query(func.sum(InvestorBehavior.volume)).filter(
        InvestorBehavior.symbol == symbol,
        InvestorBehavior.flow_type == "Exchange Inflow", # Bearish move
        InvestorBehavior.timestamp >= one_day_ago
    ).scalar() or 0

    net_flow = inflow - outflow

    # 3. DIVERGENCE LOGIC
    # CASE A: Bearish Divergence (Price Up, Whales Selling)
    if price_delta_pct > 3.0 and net_flow < 0:
        return "⚠️ BEARISH DIVERGENCE: Price is pumping, but whales are exiting. Potential trap."

    # CASE B: Bullish Divergence (Price Down, Whales Buying)
    elif price_delta_pct < -3.0 and net_flow > 0:
        return "🚀 BULLISH DIVERGENCE: Price is dipping, but whales are accumulating. Strong buy signal."

    # CASE C: Confirmation (Both moving together)
    elif price_delta_pct > 0 and net_flow > 0:
        return "✅ BULLISH CONFIRMATION: Market and whales are aligned in accumulation."

    return "Neutral: Market noise."