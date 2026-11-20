from fastapi.testclient import TestClient
from vi_inference.main import app


def test_missing_model_cannot_succeed():
    response = TestClient(app).post("/api/v1/predict", json={})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "model_not_loaded"
