"""Race database queries."""

from motor.motor_asyncio import AsyncIOMotorDatabase

from src.db.collections import collections
from src.models.race import Race, Status


async def get_all_races(
    db: AsyncIOMotorDatabase,
    season_year: int | None = None,
    circuit_id: int | None = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[Race], int]:
    """Return races, optionally filtered by season year or circuit."""
    query: dict = {}
    if season_year is not None:
        query["season_year"] = season_year
    if circuit_id is not None:
        query["circuit_id"] = circuit_id
    total = await db[collections.races].count_documents(query)
    cursor = (
        db[collections.races]
        .find(query)
        .sort([("season_year", -1), ("round", 1)])
        .skip(skip)
        .limit(limit)
    )
    races = [Race(**doc) async for doc in cursor]
    return races, total


async def get_race_by_id(race_id: int, db: AsyncIOMotorDatabase) -> Race | None:
    """Find a race by its Kaggle raceId."""
    doc = await db[collections.races].find_one({"race_id": race_id})
    if not doc:
        return None
    return Race(**doc)


async def get_race_by_season_round(
    season_year: int, round_number: int, db: AsyncIOMotorDatabase
) -> Race | None:
    """Find a specific race by season year and round number."""
    doc = await db[collections.races].find_one(
        {"season_year": season_year, "round": round_number}
    )
    if not doc:
        return None
    return Race(**doc)


async def get_all_statuses(db: AsyncIOMotorDatabase) -> list[Status]:
    """Return all race status codes."""
    cursor = db[collections.statuses].find()
    return [Status(**doc) async for doc in cursor]
