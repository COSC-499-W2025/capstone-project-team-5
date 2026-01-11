"""Tests for the Zip2Job API."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from capstone_project_team_5.api.main import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the API."""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_returns_200(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_healthy_status(self, client: TestClient) -> None:
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "healthy"

    def test_health_response_is_json(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.headers["content-type"] == "application/json"


class TestAppConfiguration:
    """Tests for the FastAPI app configuration."""

    def test_app_title(self) -> None:
        assert app.title == "Zip2Job API"

    def test_app_version(self) -> None:
        assert app.version == "0.1.0"

    def test_cors_middleware_is_configured(self) -> None:
        middleware_classes = [m.cls.__name__ for m in app.user_middleware]
        assert "CORSMiddleware" in middleware_classes


class TestInvalidRoutes:
    """Tests for handling invalid routes."""

    def test_unknown_route_returns_404(self, client: TestClient) -> None:
        response = client.get("/nonexistent")
        assert response.status_code == 404
