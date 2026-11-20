"""Heart disease detection with the XGBoost model from cardiodisease_detection/XGboost.py.

The model was trained on the UCI Heart Disease dataset (id 45, Cleveland). Its positive
class is heart disease present (the dataset's `num` > 0). The artifact here is a copy of
cardiodisease_detection/models/xgboost_model.joblib; copy it again after retraining.

It lives outside app/services/models, which Docker mounts as the trained-model volume, so
an existing volume does not hide it.
"""

import logging
import math
from pathlib import Path

import joblib
import pandas as pd
from xgboost import DMatrix

from app.schemas import HeartDiseaseField, HeartDiseaseModel, HeartDiseaseResult

logger = logging.getLogger(__name__)

MODEL_PATH = Path(__file__).resolve().parent / "heart_disease_models" / "xgboost_model.joblib"
MODEL_VERSION = "heart_disease_xgboost_v1"
THRESHOLD = 0.5


def _select(name, label, options):
    return HeartDiseaseField(
        name=name, label=label, type="select",
        options=[{"value": value, "label": text} for value, text in options],
    )


def _number(name, label, unit, low, high):
    return HeartDiseaseField(name=name, label=label, type="number", unit=unit, min=low, max=high)


# In the model's feature order. Codes follow the UCI dataset documentation.
FIELDS = [
    _number("age", "Age", "years", 1, 120),
    _select("sex", "Sex", [(0, "Female"), (1, "Male")]),
    _select("cp", "Chest pain type", [
        (1, "Typical angina"), (2, "Atypical angina"), (3, "Non-anginal pain"), (4, "Asymptomatic"),
    ]),
    _number("trestbps", "Resting blood pressure", "mm Hg", 50, 250),
    _number("chol", "Serum cholesterol", "mg/dL", 50, 700),
    _select("fbs", "Fasting blood sugar", [(0, "120 mg/dL or less"), (1, "Above 120 mg/dL")]),
    _select("restecg", "Resting ECG", [
        (0, "Normal"), (1, "ST-T wave abnormality"), (2, "Left ventricular hypertrophy"),
    ]),
    _number("thalach", "Maximum heart rate achieved", "bpm", 50, 250),
    _select("exang", "Exercise-induced angina", [(0, "No"), (1, "Yes")]),
    _number("oldpeak", "ST depression induced by exercise", "mm", 0, 10),
    _select("slope", "Slope of the peak exercise ST segment", [
        (1, "Upsloping"), (2, "Flat"), (3, "Downsloping"),
    ]),
    _select("ca", "Major vessels colored by fluoroscopy", [(n, str(n)) for n in range(4)]),
    _select("thal", "Thalassemia", [(3, "Normal"), (6, "Fixed defect"), (7, "Reversible defect")]),
]
_FIELD_NAMES = [field.name for field in FIELDS]


class HeartDiseaseInputError(ValueError):
    pass


class HeartDiseaseUnavailableError(RuntimeError):
    pass


def _load():
    """Return (model, None), or (None, reason) so the page can say why it is unavailable."""
    try:
        model = joblib.load(MODEL_PATH)
    except Exception:
        logger.exception("Could not load the heart disease model from %s", MODEL_PATH)
        return None, "The heart disease model could not be loaded on the server."
    if list(model.feature_names or []) != _FIELD_NAMES:
        logger.error("Heart disease model features %s do not match %s", model.feature_names, _FIELD_NAMES)
        return None, "The heart disease model's inputs do not match the server's field list."
    return model, None


_MODEL, _REASON = _load()


def model_config() -> HeartDiseaseModel:
    if _MODEL is None:
        return HeartDiseaseModel(available=False, reason=_REASON, modelVersion=None, fields=[])
    return HeartDiseaseModel(available=True, reason=None, modelVersion=MODEL_VERSION, fields=FIELDS)


def _validated_row(features: dict[str, float]) -> pd.DataFrame:
    missing = [name for name in _FIELD_NAMES if name not in features]
    if missing:
        raise HeartDiseaseInputError(f"Missing values for: {', '.join(missing)}.")
    unknown = sorted(set(features) - set(_FIELD_NAMES))
    if unknown:
        raise HeartDiseaseInputError(f"Unknown fields: {', '.join(unknown)}.")
    for field in FIELDS:
        value = features[field.name]
        if not math.isfinite(value):
            raise HeartDiseaseInputError(f"Enter a valid value for {field.label}.")
        if field.type == "select":
            if value not in {option.value for option in field.options}:
                raise HeartDiseaseInputError(f"Choose a listed option for {field.label}.")
        elif not field.min <= value <= field.max:
            raise HeartDiseaseInputError(
                f"{field.label} must be between {field.min:g} and {field.max:g} {field.unit}."
            )
    return pd.DataFrame([[float(features[name]) for name in _FIELD_NAMES]], columns=_FIELD_NAMES)


def predict(features: dict[str, float]) -> HeartDiseaseResult:
    if _MODEL is None:
        raise HeartDiseaseUnavailableError(_REASON)
    row = _validated_row(features)
    probability = float(_MODEL.predict(DMatrix(row))[0])
    return HeartDiseaseResult(
        predictedClass="positive" if probability >= THRESHOLD else "negative",
        positiveClassProbability=probability,
        modelVersion=MODEL_VERSION,
    )
