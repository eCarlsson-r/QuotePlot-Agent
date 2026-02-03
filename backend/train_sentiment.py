from pathlib import Path
import joblib, sklearn, os
from sklearn.svm import SVC
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline

# 1. Some basic training data to get started
# In a real app, you'd load thousands of rows from a CSV
data = [
    ("Bitcoin is going to the moon", "Bullish"),
    ("Massive dump coming for ETH", "Bearish"),
    ("The market is looking strong today", "Bullish"),
    ("Regulatory FUD is killing the price", "Bearish"),
    ("Consolidation before the next leg up", "Bullish"),
    ("Sell everything, the crash is here", "Bearish")
]

texts, labels = zip(*data)

# 2. Build a simple ML Pipeline
# TF-IDF converts text to numbers, SVC is the classifier
model = Pipeline([
    ('tfidf', TfidfVectorizer()),
    ('svc', SVC(probability=True, kernel='linear'))
])

# 3. Train it
print("🧠 Lucy is learning market sentiment...")
model.fit(texts, labels)

# 4. Save it to the exact path Lucy expects
BASE_DIR = Path(__file__).resolve().parent
save_path = "models/market_sentiment_svc.joblib"
metadata = {
    "model": model,
    "sklearn_version": sklearn.__version__,
    "python_version": os.sys.version
}

joblib.dump(metadata, BASE_DIR / save_path)
print(f"✅ Brain saved! (Sklearn: {sklearn.__version__})")