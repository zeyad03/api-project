"""Circuit database queries."""

import re

from motor.motor_asyncio import AsyncIOMotorDatabase

from src.db.collections import collections
from src.models.circuit import Circuit

REGEX_OPERATOR = "$regex"
REGEX_OPTIONS = "$options"


async def get_all_circuits(
    db: AsyncIOMotorDatabase,
    active_only: bool = False,
    country: str | None = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[Circuit], int]:
    """Return circuits, optionally filtered by active status or country."""
    query: dict = {}
    if active_only:
        query["active"] = True
    if country:
        query["country"] = {REGEX_OPERATOR: re.escape(country), REGEX_OPTIONS: "i"}
    total = await db[collections.circuits].count_documents(query)
    cursor = db[collections.circuits].find(query).skip(skip).limit(limit)
    circuits = [Circuit(**doc) async for doc in cursor]
    return circuits, total


async def get_circuit_by_id(circuit_id: int, db: AsyncIOMotorDatabase) -> Circuit | None:
    """Find a circuit by its Kaggle circuitId."""
    doc = await db[collections.circuits].find_one({"circuit_id": circuit_id})
    if not doc:
        return None
    return Circuit(**doc)


async def search_circuits(
    db: AsyncIOMotorDatabase,
    name: str | None = None,
    country: str | None = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[Circuit], int]:
    """Search circuits by name or country (case-insensitive partial match)."""
    query: dict = {}
    if name:
        query["name"] = {REGEX_OPERATOR: re.escape(name), REGEX_OPTIONS: "i"}
    if country:
        query["country"] = {REGEX_OPERATOR: re.escape(country), REGEX_OPTIONS: "i"}
    total = await db[collections.circuits].count_documents(query)
    cursor = db[collections.circuits].find(query).skip(skip).limit(limit)
    circuits = [Circuit(**doc) async for doc in cursor]
    return circuits, total
