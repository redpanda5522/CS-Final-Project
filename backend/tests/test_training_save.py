import joblib

from app.services import predictor
from app.services.training import _save_model


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
