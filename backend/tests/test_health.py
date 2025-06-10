"""Basic health check test for the API."""

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint() -> None:
    """The ``/api/health`` route should return ``{"status": "ok"}``."""

    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
