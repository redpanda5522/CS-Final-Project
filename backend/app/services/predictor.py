"""Prediction entry points used by the analysis router.

TODO(ML team): Replace the stub below with the trained model. Still to decide
(see frontend/docs/backend-handoff.md, "Decisions to settle with the ML team"):
  - The definition of success and failure, the follow-up period, the decision threshold,
    and whether the probability is calibrated.
  - The feature order the trained model expects, and how uploaded columns map to it.
  - How manual region IDs and temperature/pressure measurements map to model features.
  - The policy for missing measurements, and whether force and pressure need separate fields.
"""

import json
import logging
import re
from pathlib import Path
from uuid import uuid4

import joblib
import pandas as pd
from xgboost import DMatrix

from app.schemas import AnalysisResult, ManualAnalysisRequest, ModelName, ModelOption, PerformanceMetrics

MODEL_DIR = Path(__file__).resolve().parent / "models"
logger = logging.getLogger(__name__)

# Order and labels here are what the frontend dropdown shows (GET /api/models).
MODEL_SPECS = {
    "logistic": {"label": "Logistic regression", "file": "logistic_model.joblib", "version": "logistic_regression_v1", "type": "sklearn"},
    "random_forest": {"label": "Random forest", "file": "random_forest_model.joblib", "version": "random_forest_v1", "type": "sklearn"},
    "xgboost": {"label": "XGBoost", "file": "xgboost_model.joblib", "version": "xgboost_v1", "type": "xgb"},
    # knc.py trains a NearestCentroid classifier, despite the k_nearest ID.
    "k_nearest": {"label": "Nearest centroid", "file": "knc_model.joblib", "version": "k_nearest_v1", "type": "sklearn"},
    # "nueral": {"file": "neural_net_model.joblib", ...},
}

# Raw data.csv sub-columns are named v<number>; clean_data.py OR-s them into the named
# column before them. These are the columns clean_data.py drops before combining.
_RAW_SUBCOLUMN = re.compile(r"v\d+")
_DROPPED_BEFORE_COMBINING = [
    "ablationdata_pfa", "applications_pfa", "detectorsversion", "grids_pfa", "rawpositions_pfa",
    "sites_pfa", "visitagsessions_pfa", "visitagsettings_pfa", "vvversion", "id",
]


class PredictionInputError(ValueError):
    """The input cannot be used with the selected model (a client error)."""


class ModelUnavailableError(RuntimeError):
    """The selected model's artifact failed to load."""


def _feature_names(model) -> list[str]:
    """Columns the model was trained on, in training order."""
    names = getattr(model, "feature_names_in_", None)  # sklearn estimators and pipelines
    if names is None:
        names = model.feature_names  # xgboost Booster
    return [str(name).strip() for name in names]


def _get_class_labels(model) -> list[str]:
    """Return labels stored with trained models; old artifacts are binary 0/1."""
    labels = model.attr("class_labels") if hasattr(model, "attr") else None
    if labels is None:
        return ["0", "1"]
    parsed = json.loads(labels)
    if not isinstance(parsed, list) or not all(isinstance(label, str) for label in parsed):
        raise ValueError("The artifact has invalid class-label metadata.")
    return parsed


def _model_artifact_path(name: str, spec: dict) -> Path:
    """Use the newest trained artifact, falling back to the bundled model."""
    base = MODEL_DIR / spec["file"]
    versions = sorted(MODEL_DIR.glob(f"{base.stem}_20*{base.suffix}"))
    return versions[-1] if versions else base


def _model_metadata(model, spec: dict) -> tuple[str, PerformanceMetrics | None]:
    """Read evaluation values stored in the exact model artifact in use."""
    if not hasattr(model, "attr"):
        return spec["version"], None
    version = model.attr("model_version") or spec["version"]
    raw_metrics = model.attr("performance_metrics")
    if raw_metrics is None:
        return version, None
    return version, PerformanceMetrics.model_validate(json.loads(raw_metrics))


def _has_raw_subcolumns(columns) -> bool:
    return any(_RAW_SUBCOLUMN.fullmatch(str(column)) for column in columns)


def _load_models() -> dict[str, dict]:
    """Load each artifact independently so one bad file only disables that model."""
    models = {}
    for name, spec in MODEL_SPECS.items():
        try:
            model = joblib.load(_model_artifact_path(name, spec))
            features = _feature_names(model)
            class_labels = _get_class_labels(model)
            version, metrics = _model_metadata(model, spec)
            target_column = model.attr("target_column") if hasattr(model, "attr") else None
        except Exception:
            logger.exception("Could not load model %r from %s", name, spec["file"])
            continue
        models[name] = {
            **spec,
            "model": model,
            # Models were trained on different column sets: k_nearest on the raw columns,
            # the others on the combined ones. Each is aligned to its own list.
            "features": features,
            "raw_input": _has_raw_subcolumns(features),
            "class_labels": class_labels,
            "target_column": target_column or "recur",
            "version": version,
            "performance_metrics": metrics,
        }
    return models


MODEL_MAP = _load_models()

'''
    Register a newly trained model for use in predictions.
    @param model_name: The name of the model to register
    @param model: The trained model
'''
def register_trained_model(model_name: ModelName, model) -> None:
    """Make a newly trained in-process model available for subsequent predictions."""
    if model_name not in MODEL_SPECS:
        raise ValueError(f"Unknown model: {model_name}")
    features = _feature_names(model)
    if not features:
        raise ValueError(f"The {model_name} model has no feature names.")
    version, metrics = _model_metadata(model, MODEL_SPECS[model_name])
    MODEL_MAP[model_name] = {
        **MODEL_SPECS[model_name],
        "model": model,
        "features": features,
        "raw_input": _has_raw_subcolumns(features),
        "class_labels": _get_class_labels(model),
        "target_column": model.attr("target_column") if hasattr(model, "attr") else "recur",
        "version": version,
        "performance_metrics": metrics,
    }


# Adjust these values later
SUCCESS_THRESHOLD = 0.5
OUTCOME_DEFINITION = (
    f"Success: Greater than {SUCCESS_THRESHOLD * 100}% predicted chance "
    f"that treatment was successful. Failure: Greater than {SUCCESS_THRESHOLD * 100}% "
    f"predicted chance that treatment was unsuccessful."
)
def _result(probability: float, model_info: dict) -> AnalysisResult:
    return AnalysisResult(
        analysisId=f"analysis-{uuid4()}",
        predictedOutcome="success" if probability >= SUCCESS_THRESHOLD else "failure",
        probability=probability,
        outcomeDefinition=OUTCOME_DEFINITION,
        modelVersion=model_info["version"],
        performanceMetrics=model_info.get("performance_metrics"),
    )

def _combine_raw_columns(row: pd.DataFrame) -> pd.DataFrame:
    """Reproduce clean_data.py: OR each named column with the v-columns that follow it."""
    X = row.drop(columns=_DROPPED_BEFORE_COMBINING, errors="ignore")
    X = X.apply(pd.to_numeric, errors="coerce").fillna(0)
    groups, current = [], None
    for column in X.columns:
        # Same rule as clean_data.py: a column not starting with "v" opens a new group.
        if str(column)[0] != "v" or current is None:
            current = column
        groups.append(current)
    combined = (X != 0).T.groupby(groups, sort=False).any().T.astype(int)
    return combined


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

def _predict_sklearn(model, row: pd.DataFrame) -> float:
    # Calculate Probability of a 0 for recur (which is a successful operation)
    return model.predict_proba(row)[0][0]

def _predict_xgb(model, row: pd.DataFrame) -> float:
    # Calculate Probability of a 0 for recur (which is a successful operation)
    return 1 - model.predict(DMatrix(row))[0]

def _model_info(model_name: ModelName) -> dict:
    if model_name not in MODEL_MAP:
        raise ModelUnavailableError(f"The {model_name} model is not available on this server.")
    return MODEL_MAP[model_name]


def list_models() -> list[ModelOption]:
    """Every known model, with whether its artifact loaded and which file formats it takes."""
    options = []
    for name, spec in MODEL_SPECS.items():
        info = MODEL_MAP.get(name)
        # Combined-column models also take raw files (combined server-side); raw-only models do not.
        formats = [] if info is None else ["raw"] if info["raw_input"] else ["raw", "combined"]
        options.append(ModelOption(id=name, label=spec["label"], available=info is not None, inputFormats=formats))
    return options


def predict_from_file(row: pd.DataFrame, model_name: ModelName = "logistic") -> AnalysisResult:
    """Predict from one parsed procedure row (raw data.csv or combined columns)."""
    model_info = _model_info(model_name)
    if model_info.get("target_column", "recur") != "recur":
        raise PredictionInputError(
            "The selected model was trained for a different target and cannot be used for ablation outcome analysis."
        )
    # TODO: Remove after Multi-Class Classification is supported for analysis outcomes
    if model_info["class_labels"] != ["0", "1"]:
        labels = ", ".join(model_info["class_labels"])
        raise PredictionInputError(
            "The active model is trained for classes "
            f"[{labels}], but outcome analysis requires binary target labels 0 and 1."
        )
    row = row.rename(columns=lambda column: str(column).strip())
    row_is_raw = _has_raw_subcolumns(row.columns)
    if model_info["raw_input"] and not row_is_raw:
        raise PredictionInputError(
            f"The {model_name} model needs the raw data.csv columns (including the v-columns). "
            "This file only has the combined columns."
        )
    if row_is_raw and not model_info["raw_input"]:
        row = _combine_raw_columns(row)
    prepared_row = _prepare_features(row, model_info["features"])
    prob_of_success = None
    match model_info["type"]:
        case "sklearn":
            prob_of_success = _predict_sklearn(model_info["model"], prepared_row)
        case "xgb":
            prob_of_success = _predict_xgb(model_info["model"], prepared_row)
        case _:
            raise Exception("Invalid Model Type")
    return _result(float(prob_of_success), model_info)


def predict_from_manual(request: ManualAnalysisRequest, model_name: ModelName = "logistic") -> AnalysisResult:
    """Predict from manually entered catheter measurements."""
    # TODO(ML team): Map catheters to model features and call the model.
    model_info = _model_info(model_name)
    # The manual path is still a placeholder, so do not imply it was evaluated.
    return _result(0.5, {**model_info, "performance_metrics": None})
