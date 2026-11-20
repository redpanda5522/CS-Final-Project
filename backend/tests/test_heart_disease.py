"""Heart disease endpoints, using the bundled model."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import heart_disease

client = TestClient(app)

# A low-risk and a high-risk patient, in the UCI coding.
LOW_RISK = {"age": 35, "sex": 0, "cp": 3, "trestbps": 120, "chol": 190, "fbs": 0, "restecg": 0,
            "thalach": 180, "exang": 0, "oldpeak": 0.0, "slope": 1, "ca": 0, "thal": 3}
HIGH_RISK = {"age": 64, "sex": 1, "cp": 4, "trestbps": 150, "chol": 290, "fbs": 1, "restecg": 2,
             "thalach": 110, "exang": 1, "oldpeak": 3.0, "slope": 2, "ca": 3, "thal": 7}


def test_model_lists_fields_in_feature_order():
    body = client.get("/api/heart-disease/model").json()
    assert body["available"] is True and body["modelVersion"] == heart_disease.MODEL_VERSION
    assert [field["name"] for field in body["fields"]] == list(heart_disease._MODEL.feature_names)
    sex = next(field for field in body["fields"] if field["name"] == "sex")
    assert sex["type"] == "select" and {"value": 1, "label": "Male"} in sex["options"]


def test_predictions_follow_risk():
    low = client.post("/api/heart-disease/predict", json={"features": LOW_RISK}).json()
    high = client.post("/api/heart-disease/predict", json={"features": HIGH_RISK}).json()
    assert low["predictedClass"] == "negative" and high["predictedClass"] == "positive"
    assert low["positiveClassProbability"] < 0.5 <= high["positiveClassProbability"]
    assert high["modelVersion"] == heart_disease.MODEL_VERSION


@pytest.mark.parametrize("change, message", [
    ({"age": 500}, "Age must be between"),
    ({"thal": 4}, "Choose a listed option for Thalassemia"),
    ({"extra": 1}, "Unknown fields: extra"),
])
def test_invalid_features_are_rejected(change, message):
    response = client.post("/api/heart-disease/predict", json={"features": {**LOW_RISK, **change}})
    assert response.status_code == 422
    assert message in response.json()["detail"]


def test_missing_feature_is_rejected():
    features = {k: v for k, v in LOW_RISK.items() if k != "chol"}
    response = client.post("/api/heart-disease/predict", json={"features": features})
    assert response.status_code == 422 and "chol" in response.json()["detail"]


def test_unavailable_model(monkeypatch):
    monkeypatch.setattr(heart_disease, "_MODEL", None)
    monkeypatch.setattr(heart_disease, "_REASON", "Not loaded.")
    # Null fields are left out, which the frontend reads the same way.
    assert client.get("/api/heart-disease/model").json() == {
        "available": False, "reason": "Not loaded.", "fields": []}
    assert client.post("/api/heart-disease/predict", json={"features": LOW_RISK}).status_code == 503
