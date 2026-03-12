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
    oid = ObjectId(take_id)
    col = db[collections.hot_takes]

    # Determine which list the user is currently in (atomic read)
    doc = await col.find_one({"_id": oid})
    if not doc:
        raise HotTakeNotFoundError(take_id)

    in_agreed = user_id in doc.get("agreed_by", [])
    in_disagreed = user_id in doc.get("disagreed_by", [])

    # Remove previous reaction atomically (opposite list)
    if reaction == "agree" and in_disagreed:
        await col.update_one(
            {"_id": oid},
            {"$pull": {"disagreed_by": user_id}, "$inc": {"disagrees": -1}},
        )
    elif reaction == "disagree" and in_agreed:
        await col.update_one(
            {"_id": oid},
            {"$pull": {"agreed_by": user_id}, "$inc": {"agrees": -1}},
        )

    # Toggle the requested reaction atomically
    same_reaction = (reaction == "agree" and in_agreed) or (
        reaction == "disagree" and in_disagreed
    )
    if same_reaction:
        # Un-react: pull from current list
        field = "agreed_by" if reaction == "agree" else "disagreed_by"
        count_field = "agrees" if reaction == "agree" else "disagrees"
        await col.update_one(
            {"_id": oid},
            {"$pull": {field: user_id}, "$inc": {count_field: -1}},
        )
    else:
        # New reaction: use $addToSet (idempotent, prevents duplicates)
        field = "agreed_by" if reaction == "agree" else "disagreed_by"
        count_field = "agrees" if reaction == "agree" else "disagrees"
        await col.update_one(
            {"_id": oid},
            {"$addToSet": {field: user_id}, "$inc": {count_field: 1}},
        )

    doc = await col.find_one({"_id": oid})
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
