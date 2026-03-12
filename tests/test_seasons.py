"""Tests for /seasons endpoints.

Category: **api** – HTTP request → response tests via TestClient.
"""

import pytest
from unittest.mock import AsyncMock, patch

from src.models.season import Season

from .conftest import TIMESTAMP

pytestmark = pytest.mark.api

FAKE_SEASON_ID = "507f1f77bcf86cd799439031"


def _season(**overrides):
    defaults = dict(
        id=FAKE_SEASON_ID, year=2024,
        url="https://en.wikipedia.org/wiki/2024_Formula_One_World_Championship",
        race_count=24, sprint_round_count=6,
        opening_race="Bahrain Grand Prix",
        final_race="Abu Dhabi Grand Prix",
        champion_driver_id=1, champion_driver_name="Max Verstappen",
        champion_constructor_id=9, champion_constructor_name="Red Bull",
        created_at=TIMESTAMP,
    )
    defaults.update(overrides)
    return Season(**defaults)


# ── Public list endpoint ─────────────────────────────────────────────────────
class TestListSeasons:
    @patch("src.routers.seasons.get_all_seasons", new_callable=AsyncMock)
    def test_list_all(self, mock_get, client):
        mock_get.return_value = ([_season()], 1)
        resp = client.get("/seasons")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 1
        assert resp.json()["data"][0]["year"] == 2024
        assert resp.json()["total"] == 1

    @patch("src.routers.seasons.get_all_seasons", new_callable=AsyncMock,
           return_value=([], 0))
    def test_list_empty(self, _m, client):
        resp = client.get("/seasons")
        assert resp.status_code == 200
        assert resp.json()["data"] == []
        assert resp.json()["total"] == 0

    @patch("src.routers.seasons.get_all_seasons", new_callable=AsyncMock)
    def test_list_pagination_params(self, mock_get, client):
        mock_get.return_value = ([_season()], 75)
        resp = client.get("/seasons?skip=10&limit=5")
        assert resp.status_code == 200
        assert resp.json()["skip"] == 10
        assert resp.json()["limit"] == 5
        assert resp.json()["total"] == 75

    @patch("src.routers.seasons.get_seasons_range", new_callable=AsyncMock)
    def test_list_with_year_range(self, mock_range, client):
        mock_range.return_value = [_season()]
        resp = client.get("/seasons?start_year=2020&end_year=2024")
        assert resp.status_code == 200
        assert resp.json()["data"][0]["year"] == 2024


# ── Single-season endpoint ───────────────────────────────────────────────────
class TestGetSeason:
    @patch("src.routers.seasons.get_season_by_year", new_callable=AsyncMock)
    def test_found(self, mock_get, client):
        mock_get.return_value = _season()
        resp = client.get("/seasons/2024")
        assert resp.status_code == 200
        assert resp.json()["year"] == 2024
        assert resp.json()["champion_driver_name"] == "Max Verstappen"

    @patch("src.routers.seasons.get_season_by_year", new_callable=AsyncMock,
           return_value=None)
    def test_not_found(self, _m, client):
        resp = client.get("/seasons/1800")
        assert resp.status_code == 404
