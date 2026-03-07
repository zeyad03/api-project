"""Head-to-head vote database queries."""

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException, status

from src.db.collections import collections
from src.models.head_to_head import HeadToHeadVote, HeadToHeadVoteCreate


def _matchup_key(d1: str, d2: str) -> tuple[str, str]:
    """Ensure consistent ordering so A-vs-B and B-vs-A map to the same matchup."""
    return (min(d1, d2), max(d1, d2))


async def cast_h2h_vote(
    user_id: str, data: HeadToHeadVoteCreate, db: AsyncIOMotorDatabase
) -> HeadToHeadVote:
    d1, d2 = _matchup_key(data.driver1_id, data.driver2_id)
    if data.winner_id not in (data.driver1_id, data.driver2_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "winner_id must be one of the two drivers")

    # Upsert – one vote per user per matchup
    existing = await db[collections.head_to_head_votes].find_one(
        {"driver1_id": d1, "driver2_id": d2, "user_id": user_id}
    )
    if existing:
        await db[collections.head_to_head_votes].update_one(
            {"_id": existing["_id"]},
            {"$set": {"winner_id": data.winner_id}},
        )
        doc = await db[collections.head_to_head_votes].find_one({"_id": existing["_id"]})
    else:
        vote = HeadToHeadVote(
            driver1_id=d1, driver2_id=d2,
            user_id=user_id, winner_id=data.winner_id,
        )
        result = await db[collections.head_to_head_votes].insert_one(vote.model_dump_mongo())
        doc = await db[collections.head_to_head_votes].find_one({"_id": result.inserted_id})
    return HeadToHeadVote(**doc)


async def get_h2h_results(
    driver1_id: str, driver2_id: str, db: AsyncIOMotorDatabase
) -> dict:
    d1, d2 = _matchup_key(driver1_id, driver2_id)
    pipeline = [
        {"$match": {"driver1_id": d1, "driver2_id": d2}},
        {"$group": {"_id": "$winner_id", "votes": {"$sum": 1}}},
    ]
    results = {d1: 0, d2: 0}
    async for doc in db[collections.head_to_head_votes].aggregate(pipeline):
        results[doc["_id"]] = doc["votes"]
    total = sum(results.values())
    return {
        "driver1_id": d1,
        "driver2_id": d2,
        "driver1_votes": results[d1],
        "driver2_votes": results[d2],
        "total_votes": total,
    }
