"""Tests for /races endpoints.

Category: **api** – HTTP request → response tests via TestClient.
"""

import pytest
from unittest.mock import AsyncMock, patch

from src.models.race import Race, Status

from .conftest import TIMESTAMP

pytestmark = pytest.mark.api

FAKE_RACE_ID = "507f1f77bcf86cd799439032"


def _race(**overrides):
    defaults = dict(
        id=FAKE_RACE_ID, race_id=1100, round=1,
        name="Bahrain Grand Prix", season_year=2024,
        circuit_id=77, circuit_name="Bahrain International Circuit",
        location="Sakhir", country="Bahrain",
        date="2024-03-02", time="18:00:00",
        url="https://en.wikipedia.org/wiki/2024_Bahrain_Grand_Prix",
        has_sprint=False,
        winner_driver_id=1, winner_driver_name="Max Verstappen",
        winner_constructor_id=9, winner_constructor_name="Red Bull",
        created_at=TIMESTAMP,
    )
    defaults.update(overrides)
    return Race(**defaults)


def _status(**overrides):
    defaults = dict(id=None, status_id=1, status="Finished", created_at=TIMESTAMP)
    defaults.update(overrides)
    return Status(**defaults)


# ── Public list endpoint ─────────────────────────────────────────────────────
class TestListRaces:
    @patch("src.routers.races.get_all_races", new_callable=AsyncMock)
    def test_list_all(self, mock_get, client):
        mock_get.return_value = ([_race()], 1)
        resp = client.get("/races")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 1
        assert resp.json()["data"][0]["name"] == "Bahrain Grand Prix"
        assert resp.json()["total"] == 1

    @patch("src.routers.races.get_all_races", new_callable=AsyncMock,
           return_value=([], 0))
    def test_list_empty(self, _m, client):
        resp = client.get("/races")
        assert resp.status_code == 200
        assert resp.json()["data"] == []
        assert resp.json()["total"] == 0

    @patch("src.routers.races.get_all_races", new_callable=AsyncMock)
    def test_list_filter_by_season(self, mock_get, client):
        mock_get.return_value = ([_race()], 1)
        resp = client.get("/races?season_year=2024")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    @patch("src.routers.races.get_all_races", new_callable=AsyncMock)
    def test_list_pagination_params(self, mock_get, client):
        mock_get.return_value = ([_race()], 50)
        resp = client.get("/races?skip=5&limit=10")
        assert resp.status_code == 200
        assert resp.json()["skip"] == 5
        assert resp.json()["limit"] == 10
        assert resp.json()["total"] == 50


# ── Statuses endpoint ────────────────────────────────────────────────────────
class TestListStatuses:
    @patch("src.routers.races.get_all_statuses", new_callable=AsyncMock)
    def test_list_statuses(self, mock_get, client):
        mock_get.return_value = [_status()]
        resp = client.get("/races/statuses")
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["status"] == "Finished"


# ── Single-race endpoint ─────────────────────────────────────────────────────
class TestGetRace:
    @patch("src.routers.races.get_race_by_id", new_callable=AsyncMock)
    def test_found(self, mock_get, client):
        mock_get.return_value = _race()
        resp = client.get("/races/1100")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Bahrain Grand Prix"

    @patch("src.routers.races.get_race_by_id", new_callable=AsyncMock,
           return_value=None)
    def test_not_found(self, _m, client):
        resp = client.get("/races/9999")
        assert resp.status_code == 404


# ── Season + round lookup ───────────────────────────────────────────────────
class TestGetRaceByRound:
    @patch("src.routers.races.get_race_by_season_round", new_callable=AsyncMock)
    def test_found(self, mock_get, client):
        mock_get.return_value = _race()
        resp = client.get("/races/season/2024/round/1")
        assert resp.status_code == 200
        assert resp.json()["round"] == 1

    @patch("src.routers.races.get_race_by_season_round", new_callable=AsyncMock,
           return_value=None)
    def test_not_found(self, _m, client):
        resp = client.get("/races/season/2024/round/99")
        assert resp.status_code == 404
