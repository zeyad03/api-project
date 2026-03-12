"""Fact / trivia database queries."""

import random

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.core.exceptions import FactNotFoundError
from src.db.collections import collections
from src.models.fact import Fact, FactCreate


async def get_all_facts(
    db: AsyncIOMotorDatabase,
    category: str | None = None,
    approved_only: bool = True,
) -> list[Fact]:
    query: dict = {}
    if category:
        query["category"] = category
    if approved_only:
        query["approved"] = True
    cursor = db[collections.facts].find(query)
    return [Fact(**doc) async for doc in cursor]


async def get_random_fact(
    db: AsyncIOMotorDatabase, category: str | None = None
) -> Fact | None:
    query: dict = {"approved": True}
    if category:
        query["category"] = category
    pipeline = [{"$match": query}, {"$sample": {"size": 1}}]
    async for doc in db[collections.facts].aggregate(pipeline):
        return Fact(**doc)
    return None


async def get_fact_by_id(fact_id: str, db: AsyncIOMotorDatabase) -> Fact:
    doc = await db[collections.facts].find_one({"_id": ObjectId(fact_id)})
    if not doc:
        raise FactNotFoundError(fact_id)
    return Fact(**doc)


async def create_fact_db(
    user_id: str, data: FactCreate, db: AsyncIOMotorDatabase
) -> Fact:
    fact = Fact(submitted_by=user_id, approved=False, **data.model_dump())
    result = await db[collections.facts].insert_one(fact.model_dump_mongo())
    doc = await db[collections.facts].find_one({"_id": result.inserted_id})
    return Fact(**doc)


async def approve_fact_db(fact_id: str, db: AsyncIOMotorDatabase) -> Fact:
    result = await db[collections.facts].update_one(
        {"_id": ObjectId(fact_id)}, {"$set": {"approved": True}}
    )
    if result.matched_count == 0:
        raise FactNotFoundError(fact_id)
    doc = await db[collections.facts].find_one({"_id": ObjectId(fact_id)})
    return Fact(**doc)


async def like_fact_db(
    fact_id: str, user_id: str, db: AsyncIOMotorDatabase
) -> Fact:
    oid = ObjectId(fact_id)
    col = db[collections.facts]

    doc = await col.find_one({"_id": oid})
    if not doc:
        raise FactNotFoundError(fact_id)

    if user_id in doc.get("liked_by", []):
        # Unlike: atomic pull
        await col.update_one(
            {"_id": oid},
            {"$pull": {"liked_by": user_id}, "$inc": {"likes": -1}},
        )
    else:
        # Like: $addToSet is idempotent (prevents duplicates)
        await col.update_one(
            {"_id": oid},
            {"$addToSet": {"liked_by": user_id}, "$inc": {"likes": 1}},
        )

    doc = await col.find_one({"_id": oid})
    return Fact(**doc)


async def delete_fact_db(fact_id: str, db: AsyncIOMotorDatabase) -> bool:
    result = await db[collections.facts].delete_one({"_id": ObjectId(fact_id)})
    if result.deleted_count == 0:
        raise FactNotFoundError(fact_id)
    return True
