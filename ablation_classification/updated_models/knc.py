import json
import warnings
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy.special import expit, logit
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
    StratifiedKFold,
    cross_validate,
    train_test_split,
)
from sklearn.neighbors import NearestCentroid
from sklearn.pipeline import Pipeline

warnings.filterwarnings("ignore")

RANDOM_SEED = 45
N_SPLITS = 5

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

ablation_data = ablation_data.drop(
    columns=cols_to_drop,
    errors="ignore",
)

print(ablation_data.describe())

X = ablation_data.drop(columns=["recur"])
y = ablation_data["recur"]

# Keep numeric features only.
X = X.select_dtypes(include=["number"])

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=RANDOM_SEED,
    stratify=y,
)

# Standard sklearn pipeline. This is portable for Docker/unpickling.
pipeline = Pipeline([
    ("var", VarianceThreshold(threshold=0.05)),
    ("model", NearestCentroid(
        metric="euclidean",
        shrink_threshold=0.3,
    )),
])

cv = StratifiedKFold(
    n_splits=N_SPLITS,
    shuffle=True,
    random_state=RANDOM_SEED,
)

scoring = {
    "accuracy": "accuracy",
    "precision": "precision_weighted",
    "recall": "recall_weighted",
    "f1": "f1_weighted",
    "roc_auc": "roc_auc",
}

cv_results = cross_validate(
    pipeline,
    X_train,
    y_train,
    cv=cv,
    scoring=scoring,
    return_train_score=False,
    error_score="raise",
)

print("\n===== 5-Fold Cross-Validation Results =====")

for metric in scoring:
    scores = cv_results[f"test_{metric}"]
    print(
        f"{metric.upper()}: "
        f"{scores.mean():.4f} +/- {scores.std():.4f}"
    )

pipeline.fit(X_train, y_train)

y_pred = pipeline.predict(X_test)

# Convert NearestCentroid's decision score into success probability.
y_score = pipeline.decision_function(X_test)
probability_of_failure = expit(y_score)
y_prob_success = np.clip(
    1 - probability_of_failure,
    1e-15,
    1 - 1e-15,
)

# recur=0 represents successful treatment.
y_true_success = (y_test.to_numpy() == 0).astype(int)
y_pred_success = (y_pred == 0).astype(int)

print("\n===== Independent Test Set Results =====")
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
    confusion_matrix(
        y_true_success,
        y_pred_success,
    ),
)

print("\n===== Advanced Performance & Calibration Metrics =====")

accuracy = accuracy_score(
    y_true_success,
    y_pred_success,
)
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

logloss = log_loss(
    y_true_success,
    y_prob_success,
)
auc_score = roc_auc_score(
    y_true_success,
    y_prob_success,
)
auprc = average_precision_score(
    y_true_success,
    y_prob_success,
)
brier = brier_score_loss(
    y_true_success,
    y_prob_success,
)

print(f"Accuracy: {accuracy:.4f}")
print(f"Log Loss: {logloss:.4f}")
print(f"ROC AUC: {auc_score:.4f}")
print(f"AUPRC: {auprc:.4f}")
print(f"Brier Score: {brier:.4f}")

p_prevalence = np.mean(y_true_success)
brier_ref = p_prevalence * (1 - p_prevalence)

scaled_brier = (
    1 - (brier / brier_ref)
    if brier_ref > 0
    else 0.0
)

print(f"Scaled Brier Score: {scaled_brier:.4f}")

log_odds = logit(y_prob_success)

try:
    calib_model = LogisticRegression(
        penalty=None,
        solver="lbfgs",
    )
    calib_model.fit(
        log_odds.reshape(-1, 1),
        y_true_success,
    )

    calibration_slope = float(calib_model.coef_[0][0])
    calibration_intercept = float(
        calib_model.intercept_[0]
    )
except ValueError:
    calibration_slope = None
    calibration_intercept = None

if calibration_intercept is not None:
    print(
        "Calibration-in-the-large (Intercept): "
        f"{calibration_intercept:.4f}"
    )
else:
    print("Calibration-in-the-large (Intercept): unavailable")

if calibration_slope is not None:
    print(
        "Calibration Slope: "
        f"{calibration_slope:.4f}"
    )
else:
    print("Calibration Slope: unavailable")

observed_events = float(np.sum(y_true_success))
expected_events = float(np.sum(y_prob_success))

oe_ratio = (
    observed_events / expected_events
    if expected_events > 0
    else 1.0
)

print(
    "Observed/Expected (O/E) Ratio: "
    f"{oe_ratio:.4f}"
)

performance_metrics = {
    "accuracy": float(accuracy),
    "precision": float(precision),
    "recall": float(recall),
    "f1": float(f1),
    "auroc": float(auc_score),
    "auprc": float(auprc),
    "logLoss": float(logloss),
    "brierScore": float(brier),
    "scaledBrierScore": float(scaled_brier),
    "calibrationIntercept": calibration_intercept,
    "calibrationSlope": calibration_slope,
    "observedExpectedRatio": float(oe_ratio),
}

print("\n===== Performance Metrics Dictionary =====")
print(performance_metrics)

# Attach metadata read by predictor.py.
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
model_version = f"k_nearest_{timestamp}"

metadata = {
    "performance_metrics": json.dumps(performance_metrics),
    "model_version": model_version,
    "class_labels": json.dumps(["0", "1"]),
    "target_column": "recur",
}

pipeline.attr = metadata.get

MODEL_DIR.mkdir(parents=True, exist_ok=True)
artifact_path = MODEL_DIR / f"knc_model_{timestamp}.joblib"

joblib.dump(pipeline, artifact_path)

print(
    "\nSaved model artifact with embedded metrics to:"
    f" {artifact_path}"
)

# Permutation importance

calc_importance = False
if calc_importance:
    perm_result = permutation_importance(
        pipeline,
        X_test,
        y_test,
        scoring="roc_auc",
        n_repeats=10,
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