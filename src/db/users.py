"""User database queries."""

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.core.exceptions import EmptyUpdateError, UserNotFoundError
from src.db.collections import collections
from src.models.user import User, UserInDB, UserUpdate


async def get_user_by_id(user_id: str, db: AsyncIOMotorDatabase) -> UserInDB:
    doc = await db[collections.users].find_one({"_id": ObjectId(user_id)})
    if not doc:
        raise UserNotFoundError(user_id)
    return UserInDB(**doc)


async def get_user_by_username(username: str, db: AsyncIOMotorDatabase) -> UserInDB | None:
    doc = await db[collections.users].find_one({"username": username})
    return UserInDB(**doc) if doc else None


async def get_user_by_email(email: str, db: AsyncIOMotorDatabase) -> UserInDB | None:
    doc = await db[collections.users].find_one({"email": email})
    return UserInDB(**doc) if doc else None


async def create_user_db(user_data: dict, db: AsyncIOMotorDatabase) -> User:
    result = await db[collections.users].insert_one(user_data)
    doc = await db[collections.users].find_one({"_id": result.inserted_id})
    return User(**doc)


async def update_user_db(
    user_id: str, update: UserUpdate, db: AsyncIOMotorDatabase
) -> User:
    update_data = {k: v for k, v in update.model_dump().items() if v is not None}
    if not update_data:
        raise EmptyUpdateError("user profile")
    await db[collections.users].update_one(
        {"_id": ObjectId(user_id)}, {"$set": update_data}
    )
    doc = await db[collections.users].find_one({"_id": ObjectId(user_id)})
    if not doc:
        raise UserNotFoundError(user_id)
    return User(**doc)


async def delete_user_db(user_id: str, db: AsyncIOMotorDatabase) -> bool:
    result = await db[collections.users].delete_one({"_id": ObjectId(user_id)})
    if result.deleted_count == 0:
        raise UserNotFoundError(user_id)
    return True
