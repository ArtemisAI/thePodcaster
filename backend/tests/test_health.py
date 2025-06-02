from fastapi.testclient import TestClient # Keep for type hint if needed, or remove if not
# from backend.app.main import app # Removed, app instance comes from fixture
# client = TestClient(app) # Removed, client comes from fixture

def test_health_check(client: TestClient): # Use client fixture
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
