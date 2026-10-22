"""Model selection on both analysis endpoints.

Runs without Postgres (the session is replaced with a no-op) and without patient data
(rows are built from the columns each model was trained on).
"""

import io

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.db import get_session
from app.main import app
from app.services import predictor

SELECTABLE_MODELS = ["logistic", "random_forest", "xgboost", "k_nearest"]
COMBINED_MODELS = ["logistic", "random_forest", "xgboost"]

MANUAL_REQUEST = {
    "schemaVersion": "catheter-regions-v2",
    "groupingVersion": "left-named-column-v1",
    "units": {"temperature": "C", "pressure": "g"},
    "catheters": [
        {"id": "550e8400-e29b-41d4-a716-446655440000", "regionId": "la", "temperature": 37, "pressure": 12}
    ],
}


class NoopSession:
    def add(self, _):
        pass

    def commit(self):
        pass

    def rollback(self):
        pass


@pytest.fixture
def client():
    app.dependency_overrides[get_session] = NoopSession
    yield TestClient(app)
    app.dependency_overrides.clear()


def _csv(frame: pd.DataFrame) -> bytes:
    buffer = io.StringIO()
    frame.to_csv(buffer, index=False)
    return buffer.getvalue().encode()


def _raw_row() -> pd.DataFrame:
    """A raw data.csv-style row (k_nearest's columns) with flags set only on v-columns,
    so the named columns are 1 only if combining works."""
    columns = predictor.MODEL_MAP["k_nearest"]["features"]
    row = pd.DataFrame([[0] * len(columns)], columns=columns)
    v_columns = [c for c in columns if c[0] == "v" and c[1:].isdigit()]
    row.loc[0, v_columns[:200:5]] = 1
    return row


def _combined_by_hand(raw: pd.DataFrame) -> pd.DataFrame:
    """Independent of predictor: a named column is 1 if any v-column after it is 1."""
    combined, current = {}, None
    for column in raw.columns:
        if column[0] != "v":
            current = column
            combined[current] = int(raw.at[0, column] != 0)
        elif raw.at[0, column] != 0:
            combined[current] = 1
    return pd.DataFrame([combined])


def _upload(client, content: bytes, model_name: str | None):
    data = {} if model_name is None else {"model_name": model_name}
    return client.post("/api/analyses/file", files={"file": ("procedure.csv", content)}, data=data)


@pytest.mark.parametrize("model_name", SELECTABLE_MODELS)
def test_manual_uses_selected_model(client, model_name):
    response = client.post("/api/analyses/manual", json={**MANUAL_REQUEST, "model_name": model_name})
    assert response.status_code == 200
    body = response.json()
    assert body["modelVersion"] == predictor.MODEL_SPECS[model_name]["version"]
    assert 0 <= body["probability"] <= 1


def test_manual_defaults_to_logistic(client):
    response = client.post("/api/analyses/manual", json=MANUAL_REQUEST)
    assert response.status_code == 200
    assert response.json()["modelVersion"] == "logistic_regression_v1"


@pytest.mark.parametrize("model_name", SELECTABLE_MODELS)
def test_file_uses_selected_model(client, model_name):
    response = _upload(client, _csv(_raw_row()), model_name)
    assert response.status_code == 200
    body = response.json()
    assert body["modelVersion"] == predictor.MODEL_SPECS[model_name]["version"]
    assert 0 <= body["probability"] <= 1


def test_file_defaults_to_logistic(client):
    response = _upload(client, _csv(_raw_row()), None)
    assert response.status_code == 200
    assert response.json()["modelVersion"] == "logistic_regression_v1"


@pytest.mark.parametrize("endpoint", ["manual", "file"])
def test_unknown_model_is_rejected(client, endpoint):
    if endpoint == "manual":
        response = client.post("/api/analyses/manual", json={**MANUAL_REQUEST, "model_name": "svm"})
    else:
        response = _upload(client, _csv(_raw_row()), "svm")
    assert response.status_code == 422


def test_combine_raw_columns_matches_clean_data_rule():
    raw = pd.DataFrame([[0, 0, 1, 0, 0, 0]], columns=["la_car", "v1", "v2", "ra_car", "v3", "veins_car"])
    combined = predictor._combine_raw_columns(raw)
    # "veins_car" starts with "v", so clean_data.py folds it into "ra_car" too.
    assert combined.to_dict("records") == [{"la_car": 1, "ra_car": 0}]


@pytest.mark.parametrize("model_name", COMBINED_MODELS)
def test_raw_and_combined_files_predict_the_same(client, model_name):
    raw = _raw_row()
    combined = _combined_by_hand(raw)
    assert combined.to_numpy().sum() > 0
    from_raw = _upload(client, _csv(raw), model_name).json()["probability"]
    from_combined = _upload(client, _csv(combined), model_name).json()["probability"]
    assert from_raw == pytest.approx(from_combined)


def test_k_nearest_rejects_combined_file(client):
    combined = _combined_by_hand(_raw_row())
    response = _upload(client, _csv(combined), "k_nearest")
    assert response.status_code == 422
    assert "raw data.csv columns" in response.json()["detail"]


def test_unavailable_model_returns_503(client, monkeypatch):
    monkeypatch.delitem(predictor.MODEL_MAP, "xgboost")
    response = _upload(client, _csv(_raw_row()), "xgboost")
    assert response.status_code == 503
    assert response.json()["detail"] == "The xgboost model is not available on this server."


def test_model_failure_returns_json_500(client, monkeypatch):
    monkeypatch.setitem(predictor.MODEL_MAP, "xgboost", {**predictor.MODEL_MAP["xgboost"], "model": None})
    response = _upload(client, _csv(_raw_row()), "xgboost")
    assert response.status_code == 500
    assert response.json()["detail"] == "The xgboost model could not process this input."


def test_model_catalog_lists_every_model(client):
    response = client.get("/api/models")
    assert response.status_code == 200
    body = response.json()
    assert body["defaultModel"] == "logistic"
    assert [model["id"] for model in body["models"]] == ["logistic", "random_forest", "xgboost", "k_nearest"]
    assert all(model["available"] for model in body["models"])
    formats = {model["id"]: model["inputFormats"] for model in body["models"]}
    assert formats["k_nearest"] == ["raw"]
    assert formats["logistic"] == ["raw", "combined"]


def test_model_catalog_marks_unloaded_model_unavailable(client, monkeypatch):
    monkeypatch.delitem(predictor.MODEL_MAP, "xgboost")
    xgboost = next(m for m in client.get("/api/models").json()["models"] if m["id"] == "xgboost")
    assert xgboost == {"id": "xgboost", "label": "XGBoost", "available": False, "inputFormats": []}


def test_catalog_ids_are_exactly_the_accepted_model_names():
    from typing import get_args

    from app.schemas import ModelName

    assert list(predictor.MODEL_SPECS) == list(get_args(ModelName))
