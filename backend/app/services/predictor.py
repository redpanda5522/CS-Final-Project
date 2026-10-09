"""Prediction entry points used by the analysis router.

TODO(ML team): Replace the stub below with the trained model. Still to decide
(see frontend/docs/backend-handoff.md, "Decisions to settle with the ML team"):
  - The definition of success and failure, the follow-up period, the decision threshold,
    and whether the probability is calibrated.
  - The feature order the trained model expects, and how uploaded columns map to it.
  - How manual region IDs and temperature/pressure measurements map to model features.
  - The policy for missing measurements, and whether force and pressure need separate fields.
"""

from uuid import uuid4

import pandas as pd

from app.schemas import AnalysisResult, ManualAnalysisRequest

MODEL_VERSION = "stub-v0"
OUTCOME_DEFINITION = "Placeholder result. The outcome definition is pending from the ML team."
SUCCESS_THRESHOLD = 0.5


def _result(probability: float) -> AnalysisResult:
    return AnalysisResult(
        analysisId=f"analysis-{uuid4()}",
        predictedOutcome="success" if probability >= SUCCESS_THRESHOLD else "failure",
        probability=probability,
        outcomeDefinition=OUTCOME_DEFINITION,
        modelVersion=MODEL_VERSION,
    )


def predict_from_file(row: pd.DataFrame) -> AnalysisResult:
    """Predict from one parsed procedure row."""
    # TODO(ML team): Build the feature vector in the model's order and call the model.
    return _result(0.5)


def predict_from_manual(request: ManualAnalysisRequest) -> AnalysisResult:
    """Predict from manually entered catheter measurements."""
    # TODO(ML team): Map catheters to model features and call the model.
    return _result(0.5)
