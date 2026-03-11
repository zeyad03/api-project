"""Race result, sprint result and lap-time database queries."""

from motor.motor_asyncio import AsyncIOMotorDatabase

from src.db.collections import collections
from src.models.result import LapTimeSummary, RaceResult, SprintResult


async def get_race_results(
    db: AsyncIOMotorDatabase,
    race_id: int | None = None,
    season_year: int | None = None,
    driver_id: int | None = None,
    constructor_id: int | None = None,
    limit: int = 100,
) -> list[RaceResult]:
    """Return race results with flexible filtering."""
    query: dict = {}
    if race_id is not None:
        query["race_id"] = race_id
    if season_year is not None:
        query["season_year"] = season_year
    if driver_id is not None:
        query["driver_id"] = driver_id
    if constructor_id is not None:
        query["constructor_id"] = constructor_id
    cursor = (
        db[collections.race_results]
        .find(query)
        .sort([("season_year", -1), ("round", 1), ("position_order", 1)])
        .limit(limit)
    )
    return [RaceResult(**doc) async for doc in cursor]


async def get_sprint_results(
    db: AsyncIOMotorDatabase,
    race_id: int | None = None,
    season_year: int | None = None,
    driver_id: int | None = None,
    limit: int = 100,
) -> list[SprintResult]:
    """Return sprint results with flexible filtering."""
    query: dict = {}
    if race_id is not None:
        query["race_id"] = race_id
    if season_year is not None:
        query["season_year"] = season_year
    if driver_id is not None:
        query["driver_id"] = driver_id
    cursor = (
        db[collections.sprint_results]
        .find(query)
        .sort([("season_year", -1), ("round", 1), ("position_order", 1)])
        .limit(limit)
    )
    return [SprintResult(**doc) async for doc in cursor]


async def get_lap_time_summaries(
    db: AsyncIOMotorDatabase,
    race_id: int | None = None,
    driver_id: int | None = None,
    season_year: int | None = None,
    limit: int = 100,
) -> list[LapTimeSummary]:
    """Return lap-time summaries with flexible filtering."""
    query: dict = {}
    if race_id is not None:
        query["race_id"] = race_id
    if driver_id is not None:
        query["driver_id"] = driver_id
    if season_year is not None:
        query["season_year"] = season_year
    cursor = (
        db[collections.lap_time_summaries]
        .find(query)
        .sort([("season_year", -1), ("round", 1)])
        .limit(limit)
    )
    return [LapTimeSummary(**doc) async for doc in cursor]
