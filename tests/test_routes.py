"""Tests for API routes."""

from fastapi.testclient import TestClient


def test_health(client: TestClient):
    """GET /health returns ok status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_suggestions_missing_user_id(client: TestClient):
    """POST /api/suggestions without user_id returns 422 (Pydantic validation)."""
    response = client.post("/api/suggestions", json={})
    assert response.status_code == 422
    assert "field required" in response.text or "user_id" in response.text


def test_suggestions_nonexistent_user(client: TestClient):
    """POST /api/suggestions with unknown user_id returns 404."""
    response = client.post("/api/suggestions", json={"user_id": "nonexistent"})
    assert response.status_code == 404
