import json
import warnings
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy.special import logit
from sklearn.feature_selection import VarianceThreshold
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    classification_report,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

warnings.filterwarnings("ignore")

RANDOM_SEED = 45
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_PATH = SCRIPT_DIR / "data_combined.csv"
PROJECT_ROOT = SCRIPT_DIR.parents[1]
MODEL_DIR = PROJECT_ROOT / "backend" / "app" / "services" / "models"

# Load data
ablation_data = pd.read_csv(DATA_PATH)
ablation_data = ablation_data.dropna(subset=["recur"])

cols_to_drop = [
    "ablationdata_pfa",
    "applications_pfa",
    "detectorsversion",
    "grids_pfa",
    "rawpositions_pfa",
    "sites_pfa",
    "visitagsessions_pfa",
    "visitagsettings_pfa",
    "vvversion",
    "id",
]
ablation_data = ablation_data.drop(columns=cols_to_drop, errors="ignore")

# Separate features and target
X = ablation_data.drop(columns=["recur"])
y = ablation_data["recur"]

# Keep numeric features only
X = X.select_dtypes(include=["number"])

# Train/test split
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=RANDOM_SEED,
    stratify=y,
)

# Build pipeline
pipeline = Pipeline([
    ("var", VarianceThreshold(threshold=0.05)),
    ("model", LogisticRegression(
        penalty="l2",
        solver="liblinear",
        C=0.1,
        class_weight="balanced",
        random_state=RANDOM_SEED,
    )),
])
pipeline.fit(X_train, y_train)

# recur=0 represents success, so it is the positive class.
y_pred = pipeline.predict(X_test)
class_zero_index = list(pipeline.classes_).index(0)

y_true_success = (y_test.to_numpy() == 0).astype(int)
y_pred_success = (y_pred == 0).astype(int)
y_prob_success = np.clip(
    pipeline.predict_proba(X_test)[:, class_zero_index],
    1e-15,
    1 - 1e-15,
)

accuracy = accuracy_score(y_true_success, y_pred_success)
precision = precision_score(
    y_true_success,
    y_pred_success,
    zero_division=0,
)
recall = recall_score(
    y_true_success,
    y_pred_success,
    zero_division=0,
)
f1 = f1_score(
    y_true_success,
    y_pred_success,
    zero_division=0,
)
ll = log_loss(y_true_success, y_prob_success)
auroc = roc_auc_score(y_true_success, y_prob_success)
auprc = average_precision_score(y_true_success, y_prob_success)
brier = brier_score_loss(y_true_success, y_prob_success)

print("===== Basic Performance Metrics =====")
print("Accuracy:", accuracy)
print(
    "\nClassification Report:\n",
    classification_report(y_true_success, y_pred_success),
)
print(
    "\nConfusion Matrix:\n",
    confusion_matrix(y_true_success, y_pred_success),
)

# Scaled Brier Score
p_prev = np.mean(y_true_success)
brier_ref = p_prev * (1 - p_prev)
scaled_brier = (
    1 - (brier / brier_ref)
    if brier_ref > 0
    else 0.0
)

# Calibration intercept and slope
log_odds = logit(y_prob_success)

calib_model = LogisticRegression(
    penalty=None,
    solver="lbfgs",
)
calib_model.fit(
    log_odds.reshape(-1, 1),
    y_true_success,
)

calib_intercept = calib_model.intercept_[0]
calib_slope = calib_model.coef_[0][0]

# Observed / Expected ratio
expected_events = np.sum(y_prob_success)
oe_ratio = (
    np.sum(y_true_success) / expected_events
    if expected_events > 0
    else np.nan
)

performance_metrics = {
    "accuracy": float(accuracy),
    "precision": float(precision),
    "recall": float(recall),
    "f1": float(f1),
    "auroc": float(auroc),
    "auprc": float(auprc),
    "logLoss": float(ll),
    "brierScore": float(brier),
    "scaledBrierScore": float(scaled_brier),
    "calibrationIntercept": float(calib_intercept),
    "calibrationSlope": float(calib_slope),
    "observedExpectedRatio": float(oe_ratio),
}

print("\n===== Performance Metrics Dictionary =====")
print(performance_metrics)

# Attach metadata for predictor.py
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
model_version = f"logistic_regression_{timestamp}"

metadata = {
    "performance_metrics": json.dumps(performance_metrics),
    "model_version": model_version,
    "class_labels": json.dumps(["0", "1"]),
    "target_column": "recur",
}
pipeline.attr = metadata.get

# Save a timestamped artifact.
MODEL_DIR.mkdir(parents=True, exist_ok=True)
artifact_path = (
    MODEL_DIR / f"logistic_model_{timestamp}.joblib"
)
joblib.dump(pipeline, artifact_path)

print(
    f"\nSaved model artifact with success metrics to:"
    f" {artifact_path}"
)