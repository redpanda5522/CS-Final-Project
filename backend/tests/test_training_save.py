import joblib
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import PerformanceMetrics

from app.services import predictor
from app.services.training import _binary_metrics, _save_model, train_xgboost


def test_save_model_preserves_timestamped_versions_and_loads_newest(tmp_path, monkeypatch):
    monkeypatch.setattr(predictor, "MODEL_DIR", tmp_path)
    artifact = tmp_path / predictor.MODEL_SPECS["xgboost"]["file"]

    first_path = _save_model({"generation": 1}, artifact)
    second_path = _save_model({"generation": 2}, artifact)

    assert first_path != second_path
    assert first_path.exists()
    assert second_path.exists()
    assert not artifact.exists()
    selected_path = predictor._model_artifact_path(
        "xgboost", predictor.MODEL_SPECS["xgboost"]
    )
    assert selected_path == second_path
    assert joblib.load(selected_path) == {"generation": 2}


def test_model_artifact_path_falls_back_to_legacy_name(tmp_path, monkeypatch):
    monkeypatch.setattr(predictor, "MODEL_DIR", tmp_path)
    artifact = tmp_path / predictor.MODEL_SPECS["xgboost"]["file"]
    artifact.touch()

    assert (
        predictor._model_artifact_path("xgboost", predictor.MODEL_SPECS["xgboost"])
        == artifact
    )


def test_binary_metrics_use_success_as_positive_class():
    metrics = _binary_metrics(
        [1, 1, 0, 0], [1, 0, 0, 0], [0.9, 0.4, 0.3, 0.1]
    )

    assert metrics.accuracy == pytest.approx(0.75)
    assert metrics.precision == pytest.approx(1.0)
    assert metrics.recall == pytest.approx(0.5)
    assert metrics.f1 == pytest.approx(2 / 3)
    assert metrics.auroc == pytest.approx(1.0)
    assert metrics.auprc == pytest.approx(1.0)
    assert metrics.brierScore == pytest.approx(0.1175)
    assert metrics.observedExpectedRatio == pytest.approx(2 / 1.7)


def test_model_metadata_is_read_from_the_artifact():
    class Artifact:
        def attr(self, key):
            return {
                "model_version": "xgboost_20261111_123456",
                "performance_metrics": '{"accuracy": 0.75, "auroc": 0.9}',
            }.get(key)

    version, metrics = predictor._model_metadata(
        Artifact(), predictor.MODEL_SPECS["xgboost"]
    )
    assert version == "xgboost_20261111_123456"
    assert metrics == PerformanceMetrics(accuracy=0.75, auroc=0.9)


def test_trained_model_keeps_metrics_with_its_version(tmp_path, monkeypatch):
    monkeypatch.setattr(predictor, "MODEL_DIR", tmp_path)
    monkeypatch.setattr(predictor, "MODEL_MAP", {})
    frame = pd.DataFrame({
        "signal_a": [float(index % 7) for index in range(40)],
        "signal_b": [float(index // 2) for index in range(40)],
        "recur": [index % 2 for index in range(40)],
    })

    outcome = train_xgboost(frame, "recur")
    artifact = predictor._model_artifact_path("xgboost", predictor.MODEL_SPECS["xgboost"])
    restored = joblib.load(artifact)
    version, restored_metrics = predictor._model_metadata(
        restored, predictor.MODEL_SPECS["xgboost"]
    )
    analysis = predictor.predict_from_file(frame.drop(columns="recur").iloc[[0]], "xgboost")

    assert outcome.performance_metrics is not None
    assert outcome.performance_metrics.accuracy == outcome.accuracy
    assert restored_metrics == outcome.performance_metrics
    assert version == artifact.stem == analysis.modelVersion
    assert analysis.performanceMetrics == outcome.performance_metrics


def test_training_rejects_a_model_other_than_xgboost():
    response = TestClient(app).post(
        "/api/analyses/train",
        data={"target_column": "recur", "model_name": "logistic"},
        files={"file": ("data.csv", b"signal,recur\n1,0\n2,1\n")},
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "Only XGBoost training is supported."


def test_other_binary_target_cannot_be_used_for_ablation_analysis(tmp_path, monkeypatch):
    monkeypatch.setattr(predictor, "MODEL_DIR", tmp_path)
    monkeypatch.setattr(predictor, "MODEL_MAP", {})
    frame = pd.DataFrame({
        "signal": [float(index % 7) for index in range(40)],
        "other_disease": [index % 2 for index in range(40)],
    })

    outcome = train_xgboost(frame, "other_disease")
    assert outcome.compatible_with_outcome_analysis is False
    assert outcome.performance_metrics is None
    with pytest.raises(predictor.PredictionInputError, match="different target"):
        predictor.predict_from_file(frame.drop(columns="other_disease").iloc[[0]], "xgboost")
