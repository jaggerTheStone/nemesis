from fastapi.testclient import TestClient

from nemesis_ml.app import app


def test_health_reports_ok() -> None:
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "ml"
