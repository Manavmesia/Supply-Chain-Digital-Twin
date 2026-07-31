"""
Tests for the FastAPI application endpoints.
"""

import pytest
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


class TestRootEndpoint:
    def test_returns_200(self):
        response = client.get("/")
        assert response.status_code == 200

    def test_returns_welcome_message(self):
        response = client.get("/")
        data = response.json()
        assert "message" in data
        assert "Supply Chain" in data["message"] or "Welcome" in data["message"]


class TestHealthEndpoint:
    def test_returns_200(self):
        response = client.get("/health")
        assert response.status_code == 200

    def test_status_ok(self):
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "ok"

    def test_project_name_present(self):
        response = client.get("/health")
        data = response.json()
        assert "project" in data
        assert len(data["project"]) > 0

    def test_content_type_json(self):
        response = client.get("/health")
        assert "application/json" in response.headers["content-type"]


class TestNotFoundRoutes:
    def test_unknown_route_returns_404(self):
        response = client.get("/does-not-exist")
        assert response.status_code == 404

    def test_post_on_get_only_route_returns_405(self):
        response = client.post("/health")
        assert response.status_code == 405
