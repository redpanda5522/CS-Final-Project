import json
import warnings
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy.special import logit
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import VarianceThreshold
from sklearn.inspection import permutation_importance
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
from sklearn.model_selection import (
    RandomizedSearchCV,
    StratifiedKFold,
    train_test_split,
)
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

# Drop unwanted columns
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

# Split features and target
X = ablation_data.drop(columns=["recur"])
y = ablation_data["recur"]

# Keep numeric columns only
X = X.select_dtypes(include=["number"])

# Train/test split
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=RANDOM_SEED,
    stratify=y,
)

# Create pipeline
pipeline = Pipeline([
    ("var", VarianceThreshold()),
    (
        "model",
        RandomForestClassifier(
            random_state=RANDOM_SEED,
            class_weight="balanced",
        ),
    ),
])

# Hyperparameter search
param_dist = {
    "var__threshold": [0.01, 0.02, 0.05],
    "model__n_estimators": [100, 200, 300, 500],
    "model__max_depth": [None, 5, 10, 20, 30],
    "model__min_samples_split": [2, 5, 10],
    "model__min_samples_leaf": [1, 2, 4],
    "model__max_features": ["sqrt", "log2", None],
}

cv = StratifiedKFold(
    n_splits=5,
    shuffle=True,
    random_state=RANDOM_SEED,
)

search = RandomizedSearchCV(
    pipeline,
    param_distributions=param_dist,
    n_iter=25,
    cv=cv,
    scoring="f1_macro",
    n_jobs=-1,
    random_state=RANDOM_SEED,
)

search.fit(X_train, y_train)

best_model = search.best_estimator_
y_pred = best_model.predict(X_test)

# recur=0 represents success.
class_zero_index = list(best_model.classes_).index(0)

y_true_success = (y_test.to_numpy() == 0).astype(int)
y_pred_success = (y_pred == 0).astype(int)

y_prob_success = np.clip(
    best_model.predict_proba(X_test)[:, class_zero_index],
    1e-15,
    1 - 1e-15,
)

print("===== Basic Performance Metrics =====")
print(
    "Accuracy:",
    accuracy_score(y_true_success, y_pred_success),
)
print(
    "\nClassification Report:\n",
    classification_report(
        y_true_success,
        y_pred_success,
        zero_division=0,
    ),
)
print(
    "\nConfusion Matrix:\n",
    confusion_matrix(y_true_success, y_pred_success),
)

print("\n===== Advanced Performance & Calibration Metrics =====")

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

print(f"Accuracy                 : {accuracy:.4f}")
print(f"Log Loss                 : {ll:.4f}")
print(f"AUROC                    : {auroc:.4f}")
print(f"AUPRC                    : {auprc:.4f}")
print(f"Brier Score              : {brier:.4f}")

# Scaled Brier Score
p_prevalence = np.mean(y_true_success)
brier_ref = p_prevalence * (1 - p_prevalence)

if brier_ref > 0:
    scaled_brier = 1 - (brier / brier_ref)
else:
    scaled_brier = 0.0

print(f"Scaled Brier             : {scaled_brier:.4f}")

# Calibration intercept and slope
log_odds = logit(y_prob_success)

calibration_intercept = None
calibration_slope = None

try:
    calib_model = LogisticRegression(
        penalty=None,
        solver="lbfgs",
    )
    calib_model.fit(
        log_odds.reshape(-1, 1),
        y_true_success,
    )

    calibration_intercept = float(calib_model.intercept_[0])
    calibration_slope = float(calib_model.coef_[0][0])
except ValueError:
    pass

if calibration_intercept is not None:
    print(
        "Calibration Intercept    :"
        f" {calibration_intercept:.4f}"
    )
else:
    print("Calibration Intercept    : unavailable")

if calibration_slope is not None:
    print(
        "Calibration Slope        :"
        f" {calibration_slope:.4f}"
    )
else:
    print("Calibration Slope        : unavailable")

# Observed / Expected ratio
expected_events = float(np.sum(y_prob_success))
observed_events = float(np.sum(y_true_success))

if expected_events > 0:
    oe_ratio = observed_events / expected_events
else:
    oe_ratio = 1.0

print(f"O/E Ratio                : {oe_ratio:.4f}")

# Consolidated performance metrics
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
    "calibrationIntercept": calibration_intercept,
    "calibrationSlope": calibration_slope,
    "observedExpectedRatio": float(oe_ratio),
}

print("\n===== Performance Metrics Dictionary =====")
print(performance_metrics)

# Compute permutation importance
calc_importance = False
if calc_importance:
    perm_result = permutation_importance(
        best_model,
        X_test,
        y_test,
        scoring="roc_auc",
        n_repeats=5,
        n_jobs=-1,
        random_state=RANDOM_SEED,
    )

    feature_importances = pd.DataFrame({
        "feature": X_test.columns,
        "importance_mean": perm_result.importances_mean,
        "importance_std": perm_result.importances_std,
    }).sort_values(
        by="importance_mean",
        ascending=False,
    )

    print("\n===== Top 10 Features by Permutation Importance =====")
    print(feature_importances.head(10))

# Attach metadata expected by the backend
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
model_version = f"random_forest_{timestamp}"

metadata = {
    "performance_metrics": json.dumps(performance_metrics),
    "model_version": model_version,
    "class_labels": json.dumps(["0", "1"]),
    "target_column": "recur",
}

best_model.attr = metadata.get

# Save the timestamped artifact in the backend model directory
MODEL_DIR.mkdir(parents=True, exist_ok=True)
artifact_path = (
    MODEL_DIR
    / f"random_forest_model_{timestamp}.joblib"
)

joblib.dump(best_model, artifact_path)

print(
    "\nSaved model artifact with embedded metrics to:"
    f" {artifact_path}"
)