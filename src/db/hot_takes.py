"""Hot take database queries."""

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.core.exceptions import HotTakeDeleteNotFoundError, HotTakeNotFoundError
from src.db.collections import collections
from src.models.hot_take import HotTake, HotTakeCreate


async def get_all_hot_takes(
    db: AsyncIOMotorDatabase,
    category: str | None = None,
    sort_by: str = "recent",
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[HotTake], int]:
    query: dict = {}
    if category:
        query["category"] = category

    sort_field = {"recent": ("created_at", -1), "spicy": ("disagrees", -1), "popular": ("agrees", -1)}
    sort_key, sort_dir = sort_field.get(sort_by, ("created_at", -1))

    total = await db[collections.hot_takes].count_documents(query)
    cursor = db[collections.hot_takes].find(query).sort(sort_key, sort_dir).skip(skip).limit(limit)
    takes = [HotTake(**doc) async for doc in cursor]
    return takes, total


async def get_hot_take_by_id(take_id: str, db: AsyncIOMotorDatabase) -> HotTake:
    doc = await db[collections.hot_takes].find_one({"_id": ObjectId(take_id)})
    if not doc:
        raise HotTakeNotFoundError(take_id)
    return HotTake(**doc)


async def create_hot_take_db(
    user_id: str, display_name: str, data: HotTakeCreate, db: AsyncIOMotorDatabase
) -> HotTake:
    take = HotTake(
        user_id=user_id, user_display_name=display_name, **data.model_dump()
    )
    result = await db[collections.hot_takes].insert_one(take.model_dump_mongo())
    doc = await db[collections.hot_takes].find_one({"_id": result.inserted_id})
    return HotTake(**doc)


async def react_to_hot_take(
    take_id: str, user_id: str, reaction: str, db: AsyncIOMotorDatabase
) -> HotTake:
    doc = await db[collections.hot_takes].find_one({"_id": ObjectId(take_id)})
    if not doc:
        raise HotTakeNotFoundError(take_id)

    agreed_by = doc.get("agreed_by", [])
    disagreed_by = doc.get("disagreed_by", [])

    # Remove previous reaction if any
    if user_id in agreed_by:
        await db[collections.hot_takes].update_one(
            {"_id": ObjectId(take_id)},
            {"$pull": {"agreed_by": user_id}, "$inc": {"agrees": -1}},
        )
    if user_id in disagreed_by:
        await db[collections.hot_takes].update_one(
            {"_id": ObjectId(take_id)},
            {"$pull": {"disagreed_by": user_id}, "$inc": {"disagrees": -1}},
        )

    # Apply new reaction (toggle off if same reaction)
    already_reacted = (
        (reaction == "agree" and user_id in agreed_by)
        or (reaction == "disagree" and user_id in disagreed_by)
    )
    if not already_reacted:
        if reaction == "agree":
            await db[collections.hot_takes].update_one(
                {"_id": ObjectId(take_id)},
                {"$push": {"agreed_by": user_id}, "$inc": {"agrees": 1}},
            )
        else:
            await db[collections.hot_takes].update_one(
                {"_id": ObjectId(take_id)},
                {"$push": {"disagreed_by": user_id}, "$inc": {"disagrees": 1}},
            )

    doc = await db[collections.hot_takes].find_one({"_id": ObjectId(take_id)})
    return HotTake(**doc)


async def delete_hot_take_db(
    take_id: str, user_id: str, db: AsyncIOMotorDatabase, is_admin: bool = False
) -> bool:
    query: dict = {"_id": ObjectId(take_id)}
    if not is_admin:
        query["user_id"] = user_id
    result = await db[collections.hot_takes].delete_one(query)
    if result.deleted_count == 0:
        raise HotTakeDeleteNotFoundError(take_id)
    return True
