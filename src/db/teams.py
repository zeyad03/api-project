"""Team database queries."""

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.core.exceptions import EmptyUpdateError, TeamNotFoundError
from src.db.collections import collections
from src.models.team import (
    ConstructorResult,
    ConstructorSeasonStat,
    ConstructorStanding,
    Team,
    TeamCreate,
    TeamUpdate,
)


async def get_all_teams(db: AsyncIOMotorDatabase, active_only: bool = False) -> list[Team]:
    query = {"active": True} if active_only else {}
    cursor = db[collections.teams].find(query)
    return [Team(**doc) async for doc in cursor]


async def get_team_by_id(team_id: str, db: AsyncIOMotorDatabase) -> Team:
    doc = await db[collections.teams].find_one({"_id": ObjectId(team_id)})
    if not doc:
        raise TeamNotFoundError(team_id)
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
        raise EmptyUpdateError("team")
    await db[collections.teams].update_one(
        {"_id": ObjectId(team_id)}, {"$set": update_data}
    )
    doc = await db[collections.teams].find_one({"_id": ObjectId(team_id)})
    if not doc:
        raise TeamNotFoundError(team_id)
    return Team(**doc)


async def delete_team_db(team_id: str, db: AsyncIOMotorDatabase) -> bool:
    result = await db[collections.teams].delete_one({"_id": ObjectId(team_id)})
    if result.deleted_count == 0:
        raise TeamNotFoundError(team_id)
    return True


async def get_constructor_season_stats(
    db: AsyncIOMotorDatabase,
    constructor_id: int | None = None,
    season_year: int | None = None,
) -> list[ConstructorSeasonStat]:
    """Return constructor season stats, filtered by Kaggle constructor_id and/or season."""
    query: dict = {}
    if constructor_id is not None:
        query["constructor_id"] = constructor_id
    if season_year is not None:
        query["season_year"] = season_year
    cursor = (
        db[collections.constructor_season_stats]
        .find(query)
        .sort([("season_year", -1)])
    )
    return [ConstructorSeasonStat(**doc) async for doc in cursor]


async def get_team_stats_by_mongo_id(
    team_mongo_id: str, db: AsyncIOMotorDatabase
) -> list[ConstructorSeasonStat]:
    """Fetch season stats for a team identified by their MongoDB _id."""
    team = await get_team_by_id(team_mongo_id, db)
    if team.kaggle_constructor_id == 0:
        return []
    return await get_constructor_season_stats(
        db, constructor_id=team.kaggle_constructor_id
    )


async def get_constructor_standings(
    db: AsyncIOMotorDatabase,
    constructor_id: int | None = None,
    season_year: int | None = None,
    final_only: bool = False,
) -> list[ConstructorStanding]:
    """Return constructor standings snapshots."""
    query: dict = {}
    if constructor_id is not None:
        query["constructor_id"] = constructor_id
    if season_year is not None:
        query["season_year"] = season_year
    if final_only:
        query["is_final_race"] = True
    cursor = (
        db[collections.constructor_standings]
        .find(query)
        .sort([("season_year", -1), ("round", 1)])
    )
    return [ConstructorStanding(**doc) async for doc in cursor]


async def get_constructor_results(
    db: AsyncIOMotorDatabase,
    constructor_id: int | None = None,
    season_year: int | None = None,
) -> list[ConstructorResult]:
    """Return constructor race results."""
    query: dict = {}
    if constructor_id is not None:
        query["constructor_id"] = constructor_id
    if season_year is not None:
        query["season_year"] = season_year
    cursor = (
        db[collections.constructor_results]
        .find(query)
        .sort([("season_year", -1), ("round", 1)])
    )
    return [ConstructorResult(**doc) async for doc in cursor]
