"""Season database queries."""

from motor.motor_asyncio import AsyncIOMotorDatabase

from src.db.collections import collections
from src.models.season import Season


async def get_all_seasons(
    db: AsyncIOMotorDatabase,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[Season], int]:
    """Return all seasons ordered by year descending."""
    total = await db[collections.seasons].count_documents({})
    cursor = db[collections.seasons].find().sort("year", -1).skip(skip).limit(limit)
    seasons = [Season(**doc) async for doc in cursor]
    return seasons, total


async def get_season_by_year(year: int, db: AsyncIOMotorDatabase) -> Season | None:
    """Find a season by its championship year."""
    doc = await db[collections.seasons].find_one({"year": year})
    if not doc:
        return None
    return Season(**doc)


async def get_seasons_range(
    db: AsyncIOMotorDatabase,
    start_year: int | None = None,
    end_year: int | None = None,
) -> list[Season]:
    """Return seasons within an optional year range."""
    query: dict = {}
    if start_year is not None:
        query.setdefault("year", {})["$gte"] = start_year
    if end_year is not None:
        query.setdefault("year", {})["$lte"] = end_year
    cursor = db[collections.seasons].find(query).sort("year", -1)
    return [Season(**doc) async for doc in cursor]
