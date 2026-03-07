"""Driver database queries."""

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException, status

from src.db.collections import collections
from src.models.driver import Driver, DriverCreate, DriverUpdate


async def get_all_drivers(db: AsyncIOMotorDatabase, active_only: bool = False) -> list[Driver]:
    query = {"active": True} if active_only else {}
    cursor = db[collections.drivers].find(query)
    return [Driver(**doc) async for doc in cursor]


async def get_driver_by_id(driver_id: str, db: AsyncIOMotorDatabase) -> Driver:
    doc = await db[collections.drivers].find_one({"_id": ObjectId(driver_id)})
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Driver not found")
    return Driver(**doc)


async def search_drivers(
    db: AsyncIOMotorDatabase, name: str | None = None, team: str | None = None
) -> list[Driver]:
    query = {}
    if name:
        query["name"] = {"$regex": name, "$options": "i"}
    if team:
        query["team"] = {"$regex": team, "$options": "i"}
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
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No fields to update")
    await db[collections.drivers].update_one(
        {"_id": ObjectId(driver_id)}, {"$set": update_data}
    )
    doc = await db[collections.drivers].find_one({"_id": ObjectId(driver_id)})
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Driver not found")
    return Driver(**doc)


async def delete_driver_db(driver_id: str, db: AsyncIOMotorDatabase) -> bool:
    result = await db[collections.drivers].delete_one({"_id": ObjectId(driver_id)})
    if result.deleted_count == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Driver not found")
    return True
