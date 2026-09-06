import joblib

import sys
import os

# Get the path to the directory two levels up
# .parent.parent moves from /root/project/scripts/predict.py -> /root/project/
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent
path_to_lucy_parent = str(Path(__file__).resolve().parent.parent.parent)

# Add that directory to the Python path
if path_to_lucy_parent not in sys.path:
    sys.path.append(path_to_lucy_parent)

from lucy import text

# Load the metadata bundle
bundle = joblib.load(BASE_DIR / "models/data_questions_pipeline.joblib")
model = bundle['pipeline']

# Load vocab to process the string
r = text.readvocab(BASE_DIR / "models/data_questions_vocab.txt")
vocab, vocabidf = r[0], r[2]

# Prediction logic
sentence = "Is DES available in hardware?"
fv = text.genfeatureVectorFromString(sentence, vocab, vocabidf)

# The pipeline handles the normalization and the SVC logic automatically
pred = model.predict([fv])
prob = model.predict_proba([fv])

print(f"Result: {pred[0]} | Confidence: {max(prob[0]):.2f}")