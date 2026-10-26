"""Automated tests for root and health check endpoints."""

from fastapi.testclient import TestClient


def test_root_endpoint(client: TestClient):
    """Verify that root endpoint returns service identity and online status."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "Question Paper" in data["service"]
    assert data["documentation"] == "/docs"
    assert data["api_v1"] == "/api/v1"


def test_health_check_endpoint(client: TestClient):
    """Verify health endpoint returns valid schema and operational status."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "environment" in data
    assert "timestamp" in data
    assert "system_info" in data
    assert "python_version" in data["system_info"]
    assert "platform" in data["system_info"]


def test_cors_preflight_response(client: TestClient):
    """Verify that CORS preflight requests from authorized origins are handled."""
    headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "GET",
    }
    response = client.options("/api/v1/health", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
