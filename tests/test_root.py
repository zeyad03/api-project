"""Tests for the root health-check endpoint.

Category: **api** – HTTP request → response tests via TestClient.
"""

import pytest

pytestmark = pytest.mark.api


class TestHealthCheck:
    def test_root_returns_running(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert data["project"] == "F1 Facts API"
        assert data["version"] == "1.0.0"
        assert data["docs"] == "/docs"
