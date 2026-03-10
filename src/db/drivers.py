"""Driver database queries."""

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.core.exceptions import DriverNotFoundError, EmptyUpdateError
from src.db.collections import collections
from src.models.driver import Driver, DriverCreate, DriverUpdate

REGEX_OPERATOR = "$regex"
REGEX_OPTIONS = "$options"


async def get_all_drivers(db: AsyncIOMotorDatabase, active_only: bool = False) -> list[Driver]:
    query = {"active": True} if active_only else {}
    cursor = db[collections.drivers].find(query)
    return [Driver(**doc) async for doc in cursor]


async def get_driver_by_id(driver_id: str, db: AsyncIOMotorDatabase) -> Driver:
    doc = await db[collections.drivers].find_one({"_id": ObjectId(driver_id)})
    if not doc:
        raise DriverNotFoundError(driver_id)
    return Driver(**doc)


async def get_driver_by_name(name: str, db: AsyncIOMotorDatabase) -> Driver:
    """Find a driver by exact name (case-insensitive)."""
    doc = await db[collections.drivers].find_one(
        {"name": {REGEX_OPERATOR: f"^{name}$", REGEX_OPTIONS: "i"}}
    )
    if not doc:
        raise DriverNotFoundError(name)
    return Driver(**doc)


async def search_drivers(
    db: AsyncIOMotorDatabase, name: str | None = None, team: str | None = None
) -> list[Driver]:
    query = {}
    if name:
        query["name"] = {REGEX_OPERATOR: name, REGEX_OPTIONS: "i"}
    if team:
        query["team"] = {REGEX_OPERATOR: team, REGEX_OPTIONS: "i"}
    cursor = db[collections.drivers].find(query)
    return [Driver(**doc) async for doc in cursor]


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
    return True
