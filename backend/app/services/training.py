"""Model training services."""

import json
import logging
import math
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

import joblib
import pandas as pd
import xgboost as xgb
from xgboost import Booster
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

from app.services import predictor

logger = logging.getLogger(__name__)
BOOST_ROUNDS = 100


class TrainingDataError(ValueError):
    """The uploaded data cannot be used to train the model."""

'''
    Class representing the outcome of a model training operation.
'''
@dataclass(frozen=True)
class TrainingOutcome:
    rows_trained: int
    feature_count: int
    validation_rows: int
    accuracy: float
    classification_type: Literal["binary", "multiclass"] = "binary"
    class_labels: tuple[str, ...] = ("0", "1")
    compatible_with_outcome_analysis: bool = True

'''
    Trains an XGBoost model on the provided data.
    @param frame: The DataFrame containing the training data.
    @param target_column: The name of the column to use as the target variable.
    @returns: The outcome of the training operation.
'''
def train_xgboost(frame: pd.DataFrame, target_column: str = "recur") -> TrainingOutcome:
    """Evaluate a binary or multiclass classifier, then train it on all data."""
    features, labels, class_labels = _split_training_data(frame, target_column)
    class_count = len(class_labels)
    classification_type = "binary" if class_count == 2 else "multiclass"
    class_counts = labels.value_counts()
    if class_counts.min() < 2:
        raise TrainingDataError(
            "Training data must contain at least two rows for every target class "
            "to produce a held-out validation estimate."
        )

    # Calculate the validation size and split the data
    validation_size = max(class_count, math.ceil(len(features) * 0.2))
    train_features, validation_features, train_labels, validation_labels = train_test_split(
        features,
        labels,
        test_size=validation_size,
        random_state=42,
        stratify=labels,
    )

    # Fit the validation model and evaluate its performance
    validation_model = _fit_xgboost(train_features, train_labels, class_count, class_labels)
    validation_predictions = _predict_classes(
        validation_model, validation_features, class_count
    )
    validation_accuracy = float(accuracy_score(validation_labels, validation_predictions))

    # Save the final model
    model = _fit_xgboost(features, labels, class_count, class_labels)
    artifact = predictor.MODEL_DIR / predictor.MODEL_SPECS["xgboost"]["file"]
    _save_model(model, artifact)
    predictor.register_trained_model("xgboost", model)

    return TrainingOutcome(
        rows_trained=len(features),
        feature_count=features.shape[1],
        validation_rows=len(validation_features),
        accuracy=validation_accuracy,
        classification_type=classification_type,
        class_labels=class_labels,
        compatible_with_outcome_analysis=class_labels == ("0", "1"),
    )

'''
    Fits an XGBoost model to the provided data.
    @param features: The DataFrame containing the feature data.
    @param labels: The Series containing the target labels.
    @param class_count: The number of classes in the target variable.
    @param class_labels: A tuple of class labels.
    @returns: The fitted XGBoost model.
'''
def _fit_xgboost(
    features: pd.DataFrame,
    labels: pd.Series,
    class_count: int,
    class_labels: tuple[str, ...],
) -> Booster:
    multiclass = class_count > 2
    model = xgb.train(
        {
            "objective": "multi:softprob" if multiclass else "binary:logistic",
            "eval_metric": "mlogloss" if multiclass else "logloss",
            "max_depth": 3,
            "eta": 0.1,
            "seed": 42,
            **({"num_class": class_count} if multiclass else {}),
        },
        xgb.DMatrix(features, label=labels),
        num_boost_round=BOOST_ROUNDS,
    )
    model.set_attr(
        classification_type="multiclass" if multiclass else "binary",
        class_labels=json.dumps(class_labels),
    )
    return model

'''
    Predicts classes for the given features using the trained model.
    @param model: The trained XGBoost model.
    @param features: The DataFrame containing the feature data.
    @param class_count: The number of classes in the target variable.
    @returns: A Series containing the predicted class labels.
'''
def _predict_classes(
    model: Booster, features: pd.DataFrame, class_count: int
) -> pd.Series:
    predictions = model.predict(xgb.DMatrix(features))
    if class_count == 2:
        predicted_labels = (predictions >= 0.5).astype(int)
    else:
        predicted_labels = predictions.reshape(len(features), class_count).argmax(axis=1)
    return pd.Series(predicted_labels, index=features.index, dtype="int")


def train_logistic(frame: pd.DataFrame, target_column: str = "recur") -> tuple[int, int]:
    """Train a logistic regression model on the requested target and atomically replace its artifact."""
    features, labels, _ = _split_training_data(frame, target_column)
    # Placeholder for logistic regression training logic
    return len(features), features.shape[1]


'''
    Splits the training data into features and labels.
    @param frame: The DataFrame containing the training data.
    @param target_column: The name of the column to use as the target variable.
    @returns: A tuple containing the feature DataFrame, label Series, and class labels.
'''
def _split_training_data(
    frame: pd.DataFrame, target_column: str = "recur"
) -> tuple[pd.DataFrame, pd.Series, tuple[str, ...]]:
    
    # Input Validation
    if frame.empty:
        raise TrainingDataError("The training file contains no data rows.")

    columns = {str(column).strip().lower(): column for column in frame.columns}
    target_key = target_column.strip().lower()
    if not target_key:
        raise TrainingDataError("The target column name must not be empty.")
    actual_target_column = columns.get(target_key)
    if actual_target_column is None:
        raise TrainingDataError(
            f"The training data must include a '{target_column.strip()}' target column."
        )

    raw_labels = frame[actual_target_column]
    if raw_labels.isna().any():
        raise TrainingDataError(
            f"The '{target_column.strip()}' target column must not contain missing values."
        )
    label_values = raw_labels.tolist()
    numeric_labels = pd.to_numeric(raw_labels, errors="coerce")
    if numeric_labels.notna().all():
        if not numeric_labels.map(lambda value: math.isfinite(float(value))).all():
            raise TrainingDataError(
                f"The '{target_column.strip()}' target column must contain finite labels."
            )
        distinct_values = sorted(numeric_labels.unique().tolist())
        class_labels = tuple(_format_class_label(value) for value in distinct_values)
        label_to_index = {value: index for index, value in enumerate(distinct_values)}
        labels = numeric_labels.map(label_to_index)
    else:
        normalized_values = [str(value).strip() for value in label_values]
        if any(not value for value in normalized_values):
            raise TrainingDataError(
                f"The '{target_column.strip()}' target column must not contain empty labels."
            )
        class_labels = tuple(sorted(set(normalized_values)))
        label_to_index = {value: index for index, value in enumerate(class_labels)}
        labels = pd.Series(
            [label_to_index[value] for value in normalized_values],
            index=raw_labels.index,
        )

    if len(class_labels) < 2:
        raise TrainingDataError(
            f"Training data must include at least two classes in "
            f"'{target_column.strip()}'."
        )
    labels = labels.astype("int")

    feature_frame = frame.drop(columns=[actual_target_column, "id", "redo"], errors="ignore").copy()
    feature_frame.columns = [str(column).strip() for column in feature_frame.columns]
    if feature_frame.empty or len(feature_frame.columns) == 0:
        raise TrainingDataError("The training data must contain at least one feature column.")

    if predictor._has_raw_subcolumns(feature_frame.columns):
        feature_frame = predictor._combine_raw_columns(feature_frame)
    feature_frame = feature_frame.apply(pd.to_numeric, errors="coerce").fillna(0)
    if feature_frame.empty or not feature_frame.columns.is_unique:
        raise TrainingDataError("The training data must contain unique feature columns.")
    return feature_frame, labels, class_labels

# Formats a class label for display.
def _format_class_label(value: int | float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return str(value)

# Saves a trained model to a file with timestamp
def _save_model(model: Booster, artifact: Path) -> Path:
    artifact.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    versioned_artifact = artifact.with_name(f"{artifact.stem}_{timestamp}{artifact.suffix}")
    counter = 1
    while versioned_artifact.exists():
        versioned_artifact = artifact.with_name(f"{artifact.stem}_{timestamp}_{counter}{artifact.suffix}")
        counter += 1

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=artifact.parent,
            prefix=f".{versioned_artifact.stem}-",
            suffix=artifact.suffix,
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
        joblib.dump(model, temporary_path)
        os.replace(temporary_path, versioned_artifact)
        temporary_path = None
        return versioned_artifact
    except OSError:
        logger.exception("Could not save the trained model to %s", versioned_artifact)
        raise
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
