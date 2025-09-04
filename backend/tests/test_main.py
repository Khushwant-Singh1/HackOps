"""
Test for main application
"""
from fastapi.testclient import TestClient


def test_root_endpoint(client: TestClient):
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert data["message"] == "Welcome to HackOps API"


def test_health_endpoint(client: TestClient):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app"] == "HackOps"
    assert "version" in data


def test_api_v1_auth_endpoint(client: TestClient):
    """Test auth API endpoint"""
    response = client.get("/api/v1/auth/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Authentication API v1"


def test_api_v1_events_endpoint(client: TestClient):
    """Test events API endpoint"""
    response = client.get("/api/v1/events/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Events API v1"


def test_api_v1_teams_endpoint(client: TestClient):
    """Test teams API endpoint"""
    response = client.get("/api/v1/teams/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Teams API v1"


def test_api_v1_submissions_endpoint(client: TestClient):
    """Test submissions API endpoint"""
    response = client.get("/api/v1/submissions/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Submissions API v1"
