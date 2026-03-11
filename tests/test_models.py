"""Tests for model layer utilities and seeded document schemas.

Category: **unit** – pure logic, no HTTP or database I/O.
"""

import pytest

from bson import ObjectId

from src.models.common import MongoBase, StatusResponse, utc_now
from src.models.driver import Driver, DriverSeasonStat
from src.models.circuit import Circuit
from src.models.result import RaceResult
from src.models.season import Season
from src.models.team import Team, ConstructorSeasonStat

pytestmark = pytest.mark.unit


class TestUtcNow:
    def test_returns_iso_string(self):
        result = utc_now()
        assert isinstance(result, str)
        assert "T" in result


class TestMongoBase:
    def test_dump_mongo_converts_id_to_objectid(self):
        oid_str = "507f1f77bcf86cd799439011"
        obj = MongoBase(id=oid_str)
        dumped = obj.model_dump_mongo()
        assert isinstance(dumped["_id"], ObjectId)
        assert str(dumped["_id"]) == oid_str

    def test_dump_mongo_removes_none_id(self):
        obj = MongoBase()
        dumped = obj.model_dump_mongo()
        assert "_id" not in dumped

    def test_validate_id_converts_objectid_to_str(self):
        oid = ObjectId("507f1f77bcf86cd799439011")
        obj = MongoBase.model_validate({"_id": oid, "created_at": "2025-01-01"})
        assert obj.id == "507f1f77bcf86cd799439011"

    def test_validate_id_none_values(self):
        result = MongoBase.validate_id(None)
        assert result is None

    def test_validate_id_empty_dict(self):
        result = MongoBase.validate_id({})
        assert result == {}

    def test_validate_id_string_id_unchanged(self):
        values = {"_id": "already_string", "created_at": "2025-01-01"}
        result = MongoBase.validate_id(values)
        assert "_id" in result


class TestStatusResponse:
    def test_defaults(self):
        r = StatusResponse()
        assert r.status == "ok"
        assert r.message == ""

    def test_custom_message(self):
        r = StatusResponse(message="done")
        assert r.message == "done"


class TestSeededProfileModels:
    def test_driver_accepts_kaggle_metadata(self):
        driver = Driver(
            name="Max Verstappen",
            number=1,
            team="Red Bull",
            kaggle_driver_id=830,
            driver_ref="max_verstappen",
            code="VER",
        )
        assert driver.kaggle_driver_id == 830
        assert driver.driver_ref == "max_verstappen"
        assert driver.code == "VER"

    def test_team_accepts_kaggle_metadata(self):
        team = Team(
            name="Ferrari",
            kaggle_constructor_id=6,
            constructor_ref="ferrari",
        )
        assert team.kaggle_constructor_id == 6
        assert team.constructor_ref == "ferrari"


class TestHistoricalModels:
    def test_circuit_model_matches_seed_shape(self):
        circuit = Circuit(
            circuit_id=14,
            circuit_ref="monza",
            name="Autodromo Nazionale di Monza",
            location="Monza",
            country="Italy",
            latitude=45.6156,
            longitude=9.28111,
            altitude=162,
            race_count=74,
            first_used_year=1950,
            last_used_year=2025,
            active=True,
        )
        assert circuit.circuit_id == 14
        assert circuit.active is True

    def test_season_model_captures_titles_and_calendar(self):
        season = Season(
            year=2025,
            race_count=24,
            sprint_round_count=6,
            opening_race="Australian Grand Prix",
            final_race="Abu Dhabi Grand Prix",
            champion_driver_id=1,
            champion_driver_name="Max Verstappen",
            champion_constructor_id=9,
            champion_constructor_name="Red Bull",
        )
        assert season.year == 2025
        assert season.champion_driver_name == "Max Verstappen"

    def test_race_result_model_matches_seed_shape(self):
        result = RaceResult(
            result_id=26000,
            race_id=1120,
            season_year=2025,
            round=1,
            race_name="Australian Grand Prix",
            circuit_id=1,
            circuit_name="Albert Park Grand Prix Circuit",
            driver_id=1,
            driver_name="Max Verstappen",
            constructor_id=9,
            constructor_name="Red Bull",
            number=1,
            grid=1,
            position=1,
            position_text="1",
            position_order=1,
            points=25.0,
            laps=58,
            milliseconds=5400000,
            fastest_lap=44,
            fastest_lap_time="1:19.813",
            fastest_lap_speed=238.4,
            status_id=1,
            status="Finished",
            classified_finish=True,
        )
        assert result.result_id == 26000
        assert result.fastest_lap_speed == pytest.approx(238.4)

    def test_driver_season_stat_model_matches_seed_shape(self):
        stat = DriverSeasonStat(
            season_year=2025,
            driver_id=1,
            driver_name="Max Verstappen",
            constructor_id=9,
            constructor_name="Red Bull",
            starts=24,
            wins=12,
            podiums=18,
            poles=9,
            race_points=387.0,
            sprint_points=30.0,
            sprint_wins=3,
            sprint_podiums=5,
            classified_finishes=22,
            dnfs=2,
            best_finish=1,
            championship_position=1,
            champion=True,
            total_points=417.0,
        )
        assert stat.total_points == pytest.approx(417.0)
        assert stat.champion is True

    def test_constructor_season_stat_model_matches_seed_shape(self):
        stat = ConstructorSeasonStat(
            season_year=2025,
            constructor_id=9,
            constructor_name="Red Bull",
            race_entries=24,
            total_points=620.0,
            wins=14,
            podium_finishes=28,
            championship_position=1,
            champion=True,
        )
        assert stat.constructor_name == "Red Bull"
        assert stat.championship_position == 1
