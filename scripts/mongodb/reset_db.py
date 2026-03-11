"""Drop the configured MongoDB database before reseeding.

Uses the same settings as the app, so it works for local MongoDB or MongoDB
Atlas as long as ``MONGO_URI`` and ``DB_NAME`` are set correctly.
"""

import asyncio

from motor.motor_asyncio import AsyncIOMotorClient

from src.config.settings import settings


async def reset_db() -> None:
    client = AsyncIOMotorClient(settings.MONGO_URI)
    try:
        await client.drop_database(settings.DB_NAME)
        print(f"Dropped database: {settings.DB_NAME}")
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(reset_db())