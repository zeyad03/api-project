"""Tests for the Kaggle seed data builders."""

import pytest

from src.data.seed import (
    _build_driver_season_stats,
    _build_lap_time_summaries,
    _build_seasons,
)


def test_build_lap_time_summaries_aggregates_best_and_average_times():
    tables = {
        "lap_times.csv": [
            {"raceId": "1", "driverId": "44", "lap": "1", "milliseconds": "91000"},
            {"raceId": "1", "driverId": "44", "lap": "2", "milliseconds": "90000"},
        ],
        "races.csv": [{"raceId": "1", "year": "2025", "round": "1", "name": "Australian Grand Prix"}],
        "drivers.csv": [{"driverId": "44", "forename": "Lewis", "surname": "Hamilton"}],
        "constructors.csv": [{"constructorId": "6", "name": "Ferrari"}],
        "results.csv": [{"raceId": "1", "driverId": "44", "constructorId": "6"}],
    }

    docs = _build_lap_time_summaries(tables)

    assert len(docs) == 1
    assert docs[0]["driver_name"] == "Lewis Hamilton"
    assert docs[0]["constructor_name"] == "Ferrari"
    assert docs[0]["best_lap_time_ms"] == 90000
    assert docs[0]["average_lap_time_ms"] == pytest.approx(90500.0)


def test_build_seasons_includes_champions_and_sprint_rounds():
    tables = {
        "seasons.csv": [{"year": "2025", "url": "http://example.com/2025"}],
        "races.csv": [
            {"raceId": "1", "year": "2025", "round": "1", "name": "Australian Grand Prix"},
            {"raceId": "2", "year": "2025", "round": "2", "name": "Chinese Grand Prix"},
        ],
        "sprint_results.csv": [{"raceId": "2", "driverId": "1", "constructorId": "9"}],
        "constructors.csv": [{"constructorId": "9", "name": "Red Bull"}],
        "drivers.csv": [{"driverId": "1", "forename": "Max", "surname": "Verstappen"}],
        "constructor_standings.csv": [{"raceId": "2", "constructorId": "9", "position": "1"}],
        "driver_standings.csv": [{"raceId": "2", "driverId": "1", "position": "1"}],
    }

    docs = _build_seasons(tables)

    assert docs[0]["race_count"] == 2
    assert docs[0]["sprint_round_count"] == 1
    assert docs[0]["champion_driver_name"] == "Max Verstappen"
    assert docs[0]["champion_constructor_name"] == "Red Bull"


def test_build_driver_season_stats_combines_race_and_sprint_results():
    race_results = [
        {
            "season_year": 2025,
            "driver_id": 1,
            "driver_name": "Max Verstappen",
            "constructor_id": 9,
            "constructor_name": "Red Bull",
            "points": 25.0,
            "position_order": 1,
            "grid": 1,
            "classified_finish": True,
        },
        {
            "season_year": 2025,
            "driver_id": 1,
            "driver_name": "Max Verstappen",
            "constructor_id": 9,
            "constructor_name": "Red Bull",
            "points": 18.0,
            "position_order": 2,
            "grid": 2,
            "classified_finish": False,
        },
    ]
    sprint_results = [
        {
            "season_year": 2025,
            "driver_id": 1,
            "driver_name": "Max Verstappen",
            "constructor_id": 9,
            "constructor_name": "Red Bull",
            "points": 8.0,
            "position_order": 1,
        }
    ]
    tables = {
        "races.csv": [{"raceId": "2", "year": "2025"}],
        "driver_standings.csv": [{"raceId": "2", "driverId": "1", "position": "1"}],
    }

    docs = _build_driver_season_stats(race_results, sprint_results, tables)

    assert len(docs) == 1
    assert docs[0]["starts"] == 2
    assert docs[0]["wins"] == 1
    assert docs[0]["sprint_wins"] == 1
    assert docs[0]["dnfs"] == 1
    assert docs[0]["total_points"] == pytest.approx(51.0)
    assert docs[0]["champion"] is True