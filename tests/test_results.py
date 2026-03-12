"""Tests for /results endpoints.

Category: **api** – HTTP request → response tests via TestClient.
"""

import pytest
from unittest.mock import AsyncMock, patch

from src.models.result import LapTimeSummary, RaceResult, SprintResult

from .conftest import TIMESTAMP

pytestmark = pytest.mark.api

FAKE_RESULT_ID = "507f1f77bcf86cd799439033"


def _race_result(**overrides):
    defaults = dict(
        id=FAKE_RESULT_ID, result_id=1,
        race_id=1100, round=1, race_name="Bahrain Grand Prix",
        season_year=2024,
        driver_id=1, driver_ref="max_verstappen", driver_name="Max Verstappen",
        constructor_id=9, constructor_ref="red_bull",
        constructor_name="Red Bull",
        circuit_id=77, circuit_ref="bahrain", circuit_name="Bahrain International Circuit",
        number=1, grid=1, position=1, position_text="1", position_order=1,
        points=25.0, laps=57, time="1:31:44.742", milliseconds=5504742,
        status_id=1, status="Finished", classified_finish=True,
        fastest_lap=44, fastest_lap_time="1:32.608",
        fastest_lap_speed=206.018, created_at=TIMESTAMP,
    )
    defaults.update(overrides)
    return RaceResult(**defaults)


def _sprint_result(**overrides):
    defaults = dict(
        id=FAKE_RESULT_ID, result_id=100,
        race_id=1100, round=1, race_name="Bahrain Grand Prix",
        season_year=2024,
        driver_id=1, driver_ref="max_verstappen", driver_name="Max Verstappen",
        constructor_id=9, constructor_ref="red_bull",
        constructor_name="Red Bull",
        grid=1, position=1, position_text="1", position_order=1,
        points=8.0, laps=19, time="25:38.426", milliseconds=1538426,
        status_id=1, status="Finished", classified_finish=True,
        fastest_lap=10, fastest_lap_time="1:33.200",
        created_at=TIMESTAMP,
    )
    defaults.update(overrides)
    return SprintResult(**defaults)


def _lap_summary(**overrides):
    defaults = dict(
        id=FAKE_RESULT_ID,
        race_id=1100, round=1, race_name="Bahrain Grand Prix",
        season_year=2024,
        driver_id=1, driver_ref="max_verstappen", driver_name="Max Verstappen",
        constructor_id=9, constructor_ref="red_bull",
        constructor_name="Red Bull",
        lap_count=57, best_lap_time_ms=92608,
        best_lap_number=44, average_lap_time_ms=96574.5,
        total_lap_time_ms=5504742, created_at=TIMESTAMP,
    )
    defaults.update(overrides)
    return LapTimeSummary(**defaults)


# ── Race results endpoint ───────────────────────────────────────────────────
class TestRaceResults:
    @patch("src.routers.results.get_race_results", new_callable=AsyncMock)
    def test_list_all(self, mock_get, client):
        mock_get.return_value = [_race_result()]
        resp = client.get("/results/race")
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["driver_name"] == "Max Verstappen"

    @patch("src.routers.results.get_race_results", new_callable=AsyncMock)
    def test_filter_by_race_id(self, mock_get, client):
        mock_get.return_value = [_race_result()]
        resp = client.get("/results/race?race_id=1100")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    @patch("src.routers.results.get_race_results", new_callable=AsyncMock)
    def test_filter_by_season(self, mock_get, client):
        mock_get.return_value = [_race_result()]
        resp = client.get("/results/race?season_year=2024")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    @patch("src.routers.results.get_race_results", new_callable=AsyncMock,
           return_value=[])
    def test_empty(self, _m, client):
        resp = client.get("/results/race?driver_id=999")
        assert resp.status_code == 200
        assert resp.json() == []


# ── Sprint results endpoint ─────────────────────────────────────────────────
class TestSprintResults:
    @patch("src.routers.results.get_sprint_results", new_callable=AsyncMock)
    def test_list_all(self, mock_get, client):
        mock_get.return_value = [_sprint_result()]
        resp = client.get("/results/sprint")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    @patch("src.routers.results.get_sprint_results", new_callable=AsyncMock,
           return_value=[])
    def test_empty(self, _m, client):
        resp = client.get("/results/sprint")
        assert resp.status_code == 200
        assert resp.json() == []


# ── Lap-time summaries endpoint ─────────────────────────────────────────────
class TestLapTimeSummaries:
    @patch("src.routers.results.get_lap_time_summaries", new_callable=AsyncMock)
    def test_list_all(self, mock_get, client):
        mock_get.return_value = [_lap_summary()]
        resp = client.get("/results/lap-times")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    @patch("src.routers.results.get_lap_time_summaries", new_callable=AsyncMock)
    def test_filter_by_driver(self, mock_get, client):
        mock_get.return_value = [_lap_summary()]
        resp = client.get("/results/lap-times?driver_id=1")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    @patch("src.routers.results.get_lap_time_summaries", new_callable=AsyncMock,
           return_value=[])
    def test_empty(self, _m, client):
        resp = client.get("/results/lap-times")
        assert resp.status_code == 200
        assert resp.json() == []
