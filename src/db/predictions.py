"""Prediction database queries."""

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException, status

from src.db.collections import collections
from src.models.prediction import Prediction, PredictionCreate, PredictionUpdate, LeaderboardEntry


async def get_user_predictions(
    user_id: str, db: AsyncIOMotorDatabase,
    season: int | None = None, category: str | None = None,
) -> list[Prediction]:
    query: dict = {"user_id": user_id}
    if season:
        query["season"] = season
    if category:
        query["category"] = category
    cursor = db[collections.predictions].find(query)
    return [Prediction(**doc) async for doc in cursor]


async def get_prediction_by_id(pred_id: str, db: AsyncIOMotorDatabase) -> Prediction:
    doc = await db[collections.predictions].find_one({"_id": ObjectId(pred_id)})
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Prediction not found")
    return Prediction(**doc)


async def create_prediction_db(
    user_id: str, data: PredictionCreate, db: AsyncIOMotorDatabase
) -> Prediction:
    # Check user hasn't already predicted this category for this season
    existing = await db[collections.predictions].find_one({
        "user_id": user_id, "season": data.season, "category": data.category,
    })
    if existing:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"You already have a {data.category} prediction for {data.season}. "
            "Update or delete it instead.",
        )
    pred = Prediction(user_id=user_id, **data.model_dump())
    result = await db[collections.predictions].insert_one(pred.model_dump_mongo())
    doc = await db[collections.predictions].find_one({"_id": result.inserted_id})
    return Prediction(**doc)


async def update_prediction_db(
    pred_id: str, user_id: str, update: PredictionUpdate, db: AsyncIOMotorDatabase
) -> Prediction:
    update_data = {k: v for k, v in update.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No fields to update")
    result = await db[collections.predictions].update_one(
        {"_id": ObjectId(pred_id), "user_id": user_id}, {"$set": update_data}
    )
    if result.matched_count == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Prediction not found")
    doc = await db[collections.predictions].find_one({"_id": ObjectId(pred_id)})
    return Prediction(**doc)


async def delete_prediction_db(
    pred_id: str, user_id: str, db: AsyncIOMotorDatabase
) -> bool:
    result = await db[collections.predictions].delete_one(
        {"_id": ObjectId(pred_id), "user_id": user_id}
    )
    if result.deleted_count == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Prediction not found")
    return True


async def get_prediction_leaderboard(
    db: AsyncIOMotorDatabase, season: int, category: str
) -> list[LeaderboardEntry]:
    """Aggregate predictions to show which driver/team is most voted."""
    pipeline = [
        {"$match": {"season": season, "category": category}},
        {
            "$group": {
                "_id": {"predicted_id": "$predicted_id", "predicted_name": "$predicted_name"},
                "vote_count": {"$sum": 1},
                "avg_confidence": {"$avg": "$confidence"},
            }
        },
        {"$sort": {"vote_count": -1, "avg_confidence": -1}},
    ]
    results = []
    async for doc in db[collections.predictions].aggregate(pipeline):
        results.append(
            LeaderboardEntry(
                predicted_id=doc["_id"]["predicted_id"],
                predicted_name=doc["_id"]["predicted_name"],
                vote_count=doc["vote_count"],
                avg_confidence=round(doc["avg_confidence"], 1),
            )
        )
    return results
