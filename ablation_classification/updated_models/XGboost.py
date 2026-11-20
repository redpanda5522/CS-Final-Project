import json
import re
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
from xgboost import XGBClassifier

warnings.filterwarnings("ignore")

RANDOM_SEED = 45
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_PATH = SCRIPT_DIR / "data_combined.csv"
PROJECT_ROOT = SCRIPT_DIR.parents[1]
MODEL_DIR = PROJECT_ROOT / "backend" / "app" / "services" / "models"

COLS_TO_DROP = [
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


def build_features(frame):
    out = {}
    cf_columns = [
        column for column in frame.columns
        if re.match(r"^[a-z0-9]+_p\d+_contactforce$", column)
    ]

    regions = {
        column.split("_p")[0]
        for column in cf_columns
    }

    for region in regions:
        columns = [
            column for column in cf_columns
            if column.startswith(region + "_p")
        ]
        region_frame = frame[columns]
        out[f"{region}_cf_n_sites"] = (
            region_frame > 0
        ).sum(axis=1)
        out[f"{region}_cf_mean"] = (
            region_frame.where(region_frame > 0).mean(axis=1)
        )
        out[f"{region}_cf_max"] = region_frame.max(axis=1)

    rf_kinds = [
        "rf_",
        "temperaturesinrf_",
        "contactforceinrf_",
    ]

    for kind in rf_kinds:
        columns = [
            column for column in frame.columns
            if column.startswith(kind)
        ]
        out[f"{kind}total"] = frame[columns].sum(axis=1)
        out[f"{kind}n_nonzero"] = (
            frame[columns] > 0
        ).sum(axis=1)

    rest = [
        column for column in frame.columns
        if not re.match(
            r"^[a-z0-9]+_p\d+_contactforce$",
            column,
        )
        and not column.startswith(tuple(rf_kinds))
    ]

    return pd.concat(
        [pd.DataFrame(out), frame[rest]],
        axis=1,
    )


def create_pipeline():
    return Pipeline([
        (
            "var",
            VarianceThreshold(threshold=0.02),
        ),
        (
            "clf",
            XGBClassifier(
                eval_metric="auc",
                random_state=RANDOM_SEED,
                learning_rate=0.1,
                max_depth=3,
                n_estimators=50,
                subsample=1.0,
                colsample_bytree=1.0,
            ),
        ),
    ])


# Load data
ablation_data = pd.read_csv(DATA_PATH)
ablation_data = ablation_data.dropna(subset=["recur"])
ablation_data = ablation_data.drop(
    columns=COLS_TO_DROP,
    errors="ignore",
)

X = ablation_data.drop(columns=["recur"])
y = ablation_data["recur"]

X = X.select_dtypes(include=["number"])

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=RANDOM_SEED,
    stratify=y,
)

pipeline = create_pipeline()
pipeline.fit(X_train, y_train)

y_pred = pipeline.predict(X_test)
failure_probability = pipeline.predict_proba(X_test)[:, 1]
y_prob_success = np.clip(
    1 - failure_probability,
    1e-15,
    1 - 1e-15,
)

# recur=0 represents successful treatment.
y_true_success = (y_test.to_numpy() == 0).astype(int)
y_pred_success = (y_pred == 0).astype(int)

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

ll = log_loss(
    y_true_success,
    y_prob_success,
)
auroc = roc_auc_score(
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

print(f"Accuracy                 : {accuracy:.4f}")
print(f"Log Loss                 : {ll:.4f}")
print(f"AUROC                    : {auroc:.4f}")
print(f"AUPRC                    : {auprc:.4f}")
print(f"Brier Score              : {brier:.4f}")

p_prevalence = np.mean(y_true_success)
brier_ref = p_prevalence * (1 - p_prevalence)

if brier_ref > 0:
    scaled_brier = 1 - (brier / brier_ref)
else:
    scaled_brier = 0.0

print(f"Scaled Brier             : {scaled_brier:.4f}")

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
    calib_intercept = float(calib_model.intercept_[0])
    calib_slope = float(calib_model.coef_[0][0])
except ValueError:
    calib_intercept = None
    calib_slope = None

if calib_intercept is not None:
    print(
        "Calibration Intercept    :"
        f" {calib_intercept:.4f}"
    )
else:
    print("Calibration Intercept    : unavailable")

if calib_slope is not None:
    print(
        "Calibration Slope        :"
        f" {calib_slope:.4f}"
    )
else:
    print("Calibration Slope        : unavailable")

observed_events = float(np.sum(y_true_success))
expected_events = float(np.sum(y_prob_success))

if expected_events > 0:
    oe_ratio = observed_events / expected_events
else:
    oe_ratio = 1.0

print(f"O/E Ratio                : {oe_ratio:.4f}")

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
    "calibrationIntercept": calib_intercept,
    "calibrationSlope": calib_slope,
    "observedExpectedRatio": float(oe_ratio),
}

print("\n===== Performance Metrics Dictionary =====")
print(performance_metrics)

# Save the underlying Booster because the backend predicts with
# xgboost.DMatrix and expects type "xgb".
variance_step = pipeline.named_steps["var"]
kept_features = list(
    X_train.columns[
        variance_step.get_support()
    ]
)

booster = pipeline.named_steps["clf"].get_booster()
booster.feature_names = kept_features

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
model_version = f"xgboost_{timestamp}"

booster.set_attr(
    performance_metrics=json.dumps(performance_metrics),
    model_version=model_version,
    class_labels=json.dumps(["0", "1"]),
    target_column="recur",
)

MODEL_DIR.mkdir(parents=True, exist_ok=True)
artifact_path = (
    MODEL_DIR / f"xgboost_model_{timestamp}.joblib"
)

joblib.dump(booster, artifact_path)

print(
    "\nSaved model artifact with embedded metrics to:"
    f" {artifact_path}"
)