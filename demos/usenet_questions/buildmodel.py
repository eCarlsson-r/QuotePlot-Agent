import pandas as pd
import joblib
from sklearn import svm
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import Normalizer
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "data/data_questions_feature.csv"

# 1. Load training data
print("Loading data...")
# Using pandas is more robust for Python 3
data = pd.read_csv(MODEL_PATH)

# Assume first column is label, rest are feature vectors
y = data.iloc[:, 0].values
X = data.iloc[:, 1:].values

print(f"Dataset loaded: {X.shape[0]} samples with {X.shape[1]} features.")

# 2. Define the Modern Pipeline
# We include a Normalizer because SVMs perform significantly better 
# when feature vectors are scaled to a unit norm (common in text).
pipe = Pipeline([
    ('normalizer', Normalizer()), 
    ('svc', svm.SVC(
        C=100, 
        kernel='linear', 
        probability=True, 
        class_weight='balanced',  # <--- The "Magic" fix for Class 0
        break_ties=True # Added for better multi-class handling
    ))
])

# 3. Train the Pipeline
print("Training modern Pipeline (Normalizer + SVC)...")
pipe.fit(X, y)

# 4. Save the Pipeline using Joblib
# We save the pipeline and the number of expected features for safety
model_metadata = {
    'pipeline': pipe,
    'feature_count': X.shape[1],
    'model_version': '1.0'
}

joblib.dump(model_metadata, BASE_DIR / "models/data_questions_pipeline.joblib", compress=3)
print("Pipeline saved successfully to models/data_questions_pipeline.joblib")