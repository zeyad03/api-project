"""Driver database queries."""

import logging
import re

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.core.exceptions import DriverNotFoundError, EmptyUpdateError
from src.db.collections import collections
from src.models.driver import Driver, DriverCreate, DriverSeasonStat, DriverUpdate

REGEX_OPERATOR = "$regex"
REGEX_OPTIONS = "$options"
log = logging.getLogger("f1api.db.drivers")


async def get_all_drivers(
    db: AsyncIOMotorDatabase, active_only: bool = False,
    skip: int = 0, limit: int = 50,
) -> tuple[list[Driver], int]:
    query = {"active": True} if active_only else {}
    total = await db[collections.drivers].count_documents(query)
    cursor = db[collections.drivers].find(query).skip(skip).limit(limit)
    drivers = [Driver(**doc) async for doc in cursor]
    return drivers, total


async def get_driver_by_id(driver_id: str, db: AsyncIOMotorDatabase) -> Driver:
    doc = await db[collections.drivers].find_one({"_id": ObjectId(driver_id)})
    if not doc:
        raise DriverNotFoundError(driver_id)
    return Driver(**doc)


async def get_driver_by_name(name: str, db: AsyncIOMotorDatabase) -> Driver:
    """Find a driver by exact name (case-insensitive)."""
    doc = await db[collections.drivers].find_one(
        {"name": {REGEX_OPERATOR: f"^{re.escape(name)}$", REGEX_OPTIONS: "i"}}
    )
    if not doc:
        raise DriverNotFoundError(name)
    return Driver(**doc)


async def search_drivers(
    db: AsyncIOMotorDatabase, name: str | None = None, team: str | None = None,
    skip: int = 0, limit: int = 50,
) -> tuple[list[Driver], int]:
    query = {}
    if name:
        query["name"] = {REGEX_OPERATOR: re.escape(name), REGEX_OPTIONS: "i"}
    if team:
        query["team"] = {REGEX_OPERATOR: re.escape(team), REGEX_OPTIONS: "i"}
    total = await db[collections.drivers].count_documents(query)
    cursor = db[collections.drivers].find(query).skip(skip).limit(limit)
    drivers = [Driver(**doc) async for doc in cursor]
    return drivers, total


async def create_driver_db(driver: DriverCreate, db: AsyncIOMotorDatabase) -> Driver:
    data = Driver(**driver.model_dump()).model_dump_mongo()
    result = await db[collections.drivers].insert_one(data)
    doc = await db[collections.drivers].find_one({"_id": result.inserted_id})
    return Driver(**doc)


async def update_driver_db(
    driver_id: str, update: DriverUpdate, db: AsyncIOMotorDatabase
) -> Driver:
    update_data = {k: v for k, v in update.model_dump().items() if v is not None}
    if not update_data:
        raise EmptyUpdateError("driver")
    await db[collections.drivers].update_one(
        {"_id": ObjectId(driver_id)}, {"$set": update_data}
    )
    doc = await db[collections.drivers].find_one({"_id": ObjectId(driver_id)})
    if not doc:
        raise DriverNotFoundError(driver_id)
    return Driver(**doc)


async def delete_driver_db(driver_id: str, db: AsyncIOMotorDatabase) -> bool:
    result = await db[collections.drivers].delete_one({"_id": ObjectId(driver_id)})
    if result.deleted_count == 0:
        raise DriverNotFoundError(driver_id)

    # Cascade: remove driver from favourite lists
    removed = await db[collections.favourites].update_many(
        {"list_type": "drivers"},
        {"$pull": {"items": {"item_id": driver_id}}},
    )
    if removed.modified_count:
        log.info("Cascade: removed driver %s from %d favourite list(s)",
                 driver_id, removed.modified_count)
    return True


async def get_driver_season_stats(
    db: AsyncIOMotorDatabase,
    driver_id: int | None = None,
    season_year: int | None = None,
) -> list[DriverSeasonStat]:
    """Return driver season stats, filtered by Kaggle driver_id and/or season."""
    query: dict = {}
    if driver_id is not None:
        query["driver_id"] = driver_id
    if season_year is not None:
        query["season_year"] = season_year
    cursor = (
        db[collections.driver_season_stats]
        .find(query)
        .sort([("season_year", -1)])
    )
    return [DriverSeasonStat(**doc) async for doc in cursor]


async def get_driver_stats_by_mongo_id(
    driver_mongo_id: str, db: AsyncIOMotorDatabase
) -> list[DriverSeasonStat]:
    """Fetch season stats for a driver identified by their MongoDB _id."""
    driver = await get_driver_by_id(driver_mongo_id, db)
    if driver.kaggle_driver_id == 0:
        return []
    return await get_driver_season_stats(db, driver_id=driver.kaggle_driver_id)
