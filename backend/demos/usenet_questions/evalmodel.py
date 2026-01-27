import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn import svm
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import Normalizer
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.metrics import classification_report, roc_curve, auc
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent

# 1. Load data
print("Loading data for evaluation...")
data = pd.read_csv(BASE_DIR / "data/data_questions_feature.csv")
y = data.iloc[:, 0].values
X = data.iloc[:, 1:].values

# 2. Define the Pipeline (Must match your buildmodel.py logic)
pipeline = Pipeline([
    ('normalizer', Normalizer()), 
    ('svc', svm.SVC(
        C=100, 
        kernel='linear', 
        probability=True, 
        class_weight='balanced',  # <--- The "Magic" fix for Class 0
        break_ties=True # Added for better multi-class handling
    ))
])

# 3. Modern K-Fold Cross Validation
# StratifiedKFold is better as it preserves the percentage of samples for each class
cv = StratifiedKFold(n_splits=10, shuffle=True, random_state=42)

print("Running 10-fold cross-validation...")
# Get predictions and probabilities across all folds
y_pred = cross_val_predict(pipeline, X, y, cv=cv)
y_probas = cross_val_predict(pipeline, X, y, cv=cv, method='predict_proba')

# 4. Classification Report
target_names = ['class 0', 'class 1']
print("\nClassification Report:")
print(classification_report(y, y_pred, target_names=target_names))

# 5. ROC and AUC Calculation
plt.figure(figsize=(8, 6))

for i, label in enumerate(target_names):
    fpr, tpr, _ = roc_curve(y, y_probas[:, i], pos_label=i)
    roc_auc = auc(fpr, tpr)
    plt.plot(fpr, tpr, label=f'ROC {label} (area = {roc_auc:0.2f})')



# Plot formatting
plt.plot([0, 1], [0, 1], 'k--', label='Random Guess')
plt.xlim([0.0, 1.0])
plt.ylim([0.0, 1.05])
plt.xlabel('False Positive Rate (1 - Specificity)')
plt.ylabel('True Positive Rate (Sensitivity)')
plt.title('Receiver Operating Characteristic (ROC)')
plt.legend(loc="lower right")
plt.grid(alpha=0.3)
plt.show()