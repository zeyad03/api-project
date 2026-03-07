"""Favourite list database queries."""

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.core.exceptions import (
    DuplicateFavouriteItemError,
    EmptyUpdateError,
    FavouriteListNotFoundError,
)
from src.db.collections import collections
from src.models.favourite import FavouriteList, FavouriteListCreate, FavouriteListUpdate, AddFavouriteItem
from src.models.common import utc_now


async def get_user_favourites(
    user_id: str, db: AsyncIOMotorDatabase, list_type: str | None = None
) -> list[FavouriteList]:
    query: dict = {"user_id": user_id}
    if list_type:
        query["list_type"] = list_type
    cursor = db[collections.favourites].find(query)
    return [FavouriteList(**doc) async for doc in cursor]


async def get_favourite_by_id(
    fav_id: str, user_id: str, db: AsyncIOMotorDatabase
) -> FavouriteList:
    doc = await db[collections.favourites].find_one(
        {"_id": ObjectId(fav_id), "user_id": user_id}
    )
    if not doc:
        raise FavouriteListNotFoundError(fav_id)
    return FavouriteList(**doc)


async def create_favourite_db(
    user_id: str, data: FavouriteListCreate, db: AsyncIOMotorDatabase
) -> FavouriteList:
    fav = FavouriteList(user_id=user_id, **data.model_dump())
    result = await db[collections.favourites].insert_one(fav.model_dump_mongo())
    doc = await db[collections.favourites].find_one({"_id": result.inserted_id})
    return FavouriteList(**doc)


async def update_favourite_db(
    fav_id: str, user_id: str, update: FavouriteListUpdate, db: AsyncIOMotorDatabase
) -> FavouriteList:
    update_data = {k: v for k, v in update.model_dump().items() if v is not None}
    if not update_data:
        raise EmptyUpdateError("favourite list")
    update_data["updated_at"] = utc_now()
    result = await db[collections.favourites].update_one(
        {"_id": ObjectId(fav_id), "user_id": user_id}, {"$set": update_data}
    )
    if result.matched_count == 0:
        raise FavouriteListNotFoundError(fav_id)
    doc = await db[collections.favourites].find_one({"_id": ObjectId(fav_id)})
    return FavouriteList(**doc)


async def delete_favourite_db(
    fav_id: str, user_id: str, db: AsyncIOMotorDatabase
) -> bool:
    result = await db[collections.favourites].delete_one(
        {"_id": ObjectId(fav_id), "user_id": user_id}
    )
    if result.deleted_count == 0:
        raise FavouriteListNotFoundError(fav_id)
    return True


async def add_item_to_favourite(
    fav_id: str, user_id: str, item: AddFavouriteItem, db: AsyncIOMotorDatabase
) -> FavouriteList:
    # Check list exists and belongs to user
    doc = await db[collections.favourites].find_one(
        {"_id": ObjectId(fav_id), "user_id": user_id}
    )
    if not doc:
        raise FavouriteListNotFoundError(fav_id)

    # Check for duplicates
    existing_items = doc.get("items", [])
    if any(i["item_id"] == item.item_id for i in existing_items):
        raise DuplicateFavouriteItemError(item.name)

    await db[collections.favourites].update_one(
        {"_id": ObjectId(fav_id)},
        {
            "$push": {"items": item.model_dump()},
            "$set": {"updated_at": utc_now()},
        },
    )
    doc = await db[collections.favourites].find_one({"_id": ObjectId(fav_id)})
    return FavouriteList(**doc)


async def remove_item_from_favourite(
    fav_id: str, user_id: str, item_id: str, db: AsyncIOMotorDatabase
) -> FavouriteList:
    result = await db[collections.favourites].update_one(
        {"_id": ObjectId(fav_id), "user_id": user_id},
        {
            "$pull": {"items": {"item_id": item_id}},
            "$set": {"updated_at": utc_now()},
        },
    )
    if result.matched_count == 0:
        raise FavouriteListNotFoundError(fav_id)
    doc = await db[collections.favourites].find_one({"_id": ObjectId(fav_id)})
    return FavouriteList(**doc)
