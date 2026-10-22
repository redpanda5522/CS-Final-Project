"""Prediction entry points used by the analysis router.

TODO(ML team): Replace the stub below with the trained model. Still to decide
(see frontend/docs/backend-handoff.md, "Decisions to settle with the ML team"):
  - The definition of success and failure, the follow-up period, the decision threshold,
    and whether the probability is calibrated.
  - The feature order the trained model expects, and how uploaded columns map to it.
  - How manual region IDs and temperature/pressure measurements map to model features.
  - The policy for missing measurements, and whether force and pressure need separate fields.
"""

import joblib
import pandas as pd
from xgboost import DMatrix
from pathlib import Path
from uuid import uuid4

from app.schemas import AnalysisResult, ManualAnalysisRequest, ModelName

MODEL_DIR = Path(__file__).resolve().parent / "models"
MODEL_MAP = {
    "logistic": {
        "model": joblib.load(MODEL_DIR / "logistic_model.joblib"), 
        "version": "logistic_regression_v1", 
        "type": "sklearn"
    },
    "random_forest": {
        "model": joblib.load(MODEL_DIR / "random_forest_model.joblib"), 
        "version":"random_forest_v1", 
        "type": "sklearn"
    },
    "k_nearest": {
            "model": joblib.load(MODEL_DIR / "knc_model.joblib"), 
            "version":"k_nearest_v1", 
            "type": "sklearn"
    },
    "xgboost": {
        "model": joblib.load(MODEL_DIR / "xgboost_model.joblib"), 
        "version": "xgboost_v1", 
        "type": "xgb"
    },
    #"nueral": joblib.load(MODEL_DIR / "neural_net_model.joblib"),
}


def _feature_names(model) -> list[str]:
    """Columns the model was trained on, in training order."""
    names = getattr(model, "feature_names_in_", None)  # sklearn estimators and pipelines
    if names is None:
        names = model.feature_names  # xgboost Booster
    return [str(name).strip() for name in names]


# Models were trained on different column sets (k_nearest uses the raw columns, the
# others the combined ones), so each is aligned to its own list.
for _info in MODEL_MAP.values():
    _info["features"] = _feature_names(_info["model"])

# Adjust these values later
SUCCESS_THRESHOLD = 0.5
OUTCOME_DEFINITION = (
    f"Success: Greater than {SUCCESS_THRESHOLD * 100}% predicted chance "
    f"that treatment was successful. Failure: Greater than {SUCCESS_THRESHOLD * 100}% "
    f"predicted chance that treatment was unsuccessful."
)
def _result(probability: float, model_version: str) -> AnalysisResult:
    return AnalysisResult(
        analysisId=f"analysis-{uuid4()}",
        predictedOutcome="success" if probability >= SUCCESS_THRESHOLD else "failure",
        probability=probability,
        outcomeDefinition=OUTCOME_DEFINITION,
        modelVersion=model_version,
    )

def _prepare_features(row: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    """Align the uploaded single-row DataFrame to the model's `features`.

    - Adds any missing features with value 0.
    - Drops any extra columns not in `features`.
    - Coerces all columns to numeric where possible and fills NaN with 0.
    """
    X = row.copy()
    # Normalize incoming column names
    X.columns = [str(c).strip() for c in X.columns]
    expected = features
    # add missing expected features with 0
    for feat in expected:
        if feat not in X.columns:
            X[feat] = 0
    # reindex to expected order (drops extras)
    X = X.reindex(columns=expected)
    # coerce to numeric and fill NaN
    for col in X.columns:
        X[col] = pd.to_numeric(X[col], errors="coerce").fillna(0)
    return X

def _predict_sklearn(model, row: pd.DataFrame) -> int:
    # Calculate Probability of a 0 for recur (which is a successful operation)
    return model.predict_proba(row)[0][0]

def _predict_xgb(model, row: pd.DataFrame) -> int:
    # Calculate Probability of a 0 for recur (which is a successful operation)
    return 1 - model.predict(DMatrix(row))[0]

def predict_from_file(row: pd.DataFrame, model_name: ModelName = "logistic") -> AnalysisResult:
    """Predict from one parsed procedure row."""
    model_info = MODEL_MAP[model_name]
    prepared_row = _prepare_features(row, model_info["features"])
    prob_of_success = None
    match model_info["type"]:
        case "sklearn":
            prob_of_success = _predict_sklearn(model_info["model"], prepared_row)
        case "xgb":
            prob_of_success = _predict_xgb(model_info["model"], prepared_row)
        case _:
            raise Exception("Invalid Model Type")
    return _result(prob_of_success, model_info["version"])


def predict_from_manual(request: ManualAnalysisRequest, model_name: ModelName = "logistic") -> AnalysisResult:
    """Predict from manually entered catheter measurements."""
    # TODO(ML team): Map catheters to model features and call the model.
    model_info = MODEL_MAP[model_name]
    return _result(0.5, model_info["version"])

