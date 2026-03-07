"""Team database queries."""

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException, status

from src.db.collections import collections
from src.models.team import Team, TeamCreate, TeamUpdate


async def get_all_teams(db: AsyncIOMotorDatabase, active_only: bool = False) -> list[Team]:
    query = {"active": True} if active_only else {}
    cursor = db[collections.teams].find(query)
    return [Team(**doc) async for doc in cursor]


async def get_team_by_id(team_id: str, db: AsyncIOMotorDatabase) -> Team:
    doc = await db[collections.teams].find_one({"_id": ObjectId(team_id)})
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Team not found")
    return Team(**doc)


async def search_teams(db: AsyncIOMotorDatabase, name: str | None = None) -> list[Team]:
    query = {}
    if name:
        query["name"] = {"$regex": name, "$options": "i"}
    cursor = db[collections.teams].find(query)
    return [Team(**doc) async for doc in cursor]


async def create_team_db(team: TeamCreate, db: AsyncIOMotorDatabase) -> Team:
    data = Team(**team.model_dump()).model_dump_mongo()
    result = await db[collections.teams].insert_one(data)
    doc = await db[collections.teams].find_one({"_id": result.inserted_id})
    return Team(**doc)


async def update_team_db(
    team_id: str, update: TeamUpdate, db: AsyncIOMotorDatabase
) -> Team:
    update_data = {k: v for k, v in update.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No fields to update")
    await db[collections.teams].update_one(
        {"_id": ObjectId(team_id)}, {"$set": update_data}
    )
    doc = await db[collections.teams].find_one({"_id": ObjectId(team_id)})
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Team not found")
    return Team(**doc)


async def delete_team_db(team_id: str, db: AsyncIOMotorDatabase) -> bool:
    result = await db[collections.teams].delete_one({"_id": ObjectId(team_id)})
    if result.deleted_count == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Team not found")
    return True
