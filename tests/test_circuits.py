"""Tests for /circuits endpoints.

Category: **api** – HTTP request → response tests via TestClient.
"""

import pytest
from unittest.mock import AsyncMock, patch

from src.models.circuit import Circuit

from .conftest import TIMESTAMP

pytestmark = pytest.mark.api

FAKE_CIRCUIT_ID = "507f1f77bcf86cd799439030"


def _circuit(**overrides):
    defaults = dict(
        id=FAKE_CIRCUIT_ID, circuit_id=1, circuit_ref="monza",
        name="Autodromo Nazionale di Monza", location="Monza",
        country="Italy", latitude=45.6156, longitude=9.2811,
        altitude=162, url="https://en.wikipedia.org/wiki/Monza",
        race_count=72, first_used_year=1950, last_used_year=2024,
        active=True, created_at=TIMESTAMP,
    )
    defaults.update(overrides)
    return Circuit(**defaults)


# ── Public list endpoint ─────────────────────────────────────────────────────
class TestListCircuits:
    @patch("src.routers.circuits.get_all_circuits", new_callable=AsyncMock)
    def test_list_all(self, mock_get, client):
        mock_get.return_value = ([_circuit()], 1)
        resp = client.get("/circuits")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 1
        assert resp.json()["data"][0]["name"] == "Autodromo Nazionale di Monza"
        assert resp.json()["total"] == 1

    @patch("src.routers.circuits.get_all_circuits", new_callable=AsyncMock)
    def test_list_active_only(self, mock_get, client):
        mock_get.return_value = ([_circuit()], 1)
        resp = client.get("/circuits?active_only=true")
        assert resp.status_code == 200
        mock_get.assert_awaited_once()

    @patch("src.routers.circuits.get_all_circuits", new_callable=AsyncMock,
           return_value=([], 0))
    def test_list_empty(self, _m, client):
        resp = client.get("/circuits")
        assert resp.status_code == 200
        assert resp.json()["data"] == []
        assert resp.json()["total"] == 0

    @patch("src.routers.circuits.get_all_circuits", new_callable=AsyncMock)
    def test_list_with_country_filter(self, mock_get, client):
        mock_get.return_value = ([_circuit()], 1)
        resp = client.get("/circuits?country=Italy")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    @patch("src.routers.circuits.get_all_circuits", new_callable=AsyncMock)
    def test_list_pagination_params(self, mock_get, client):
        mock_get.return_value = ([_circuit()], 5)
        resp = client.get("/circuits?skip=2&limit=1")
        assert resp.status_code == 200
        assert resp.json()["skip"] == 2
        assert resp.json()["limit"] == 1
        assert resp.json()["total"] == 5


# ── Search endpoint ──────────────────────────────────────────────────────────
class TestSearchCircuits:
    @patch("src.routers.circuits.search_circuits", new_callable=AsyncMock)
    def test_search_by_name(self, mock_search, client):
        mock_search.return_value = ([_circuit()], 1)
        resp = client.get("/circuits/search?name=Monza")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 1

    @patch("src.routers.circuits.search_circuits", new_callable=AsyncMock)
    def test_search_by_country(self, mock_search, client):
        mock_search.return_value = ([_circuit()], 1)
        resp = client.get("/circuits/search?country=Italy")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 1

    @patch("src.routers.circuits.search_circuits", new_callable=AsyncMock,
           return_value=([], 0))
    def test_search_no_results(self, _m, client):
        resp = client.get("/circuits/search?name=Nonexistent")
        assert resp.status_code == 200
        assert resp.json()["data"] == []


# ── Single-circuit endpoint ──────────────────────────────────────────────────
class TestGetCircuit:
    @patch("src.routers.circuits.get_circuit_by_id", new_callable=AsyncMock)
    def test_found(self, mock_get, client):
        mock_get.return_value = _circuit()
        resp = client.get("/circuits/1")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Autodromo Nazionale di Monza"

    @patch("src.routers.circuits.get_circuit_by_id", new_callable=AsyncMock,
           return_value=None)
    def test_not_found(self, _m, client):
        resp = client.get("/circuits/9999")
        assert resp.status_code == 404
