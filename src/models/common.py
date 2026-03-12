"""Shared base classes and utilities for all models."""

from datetime import datetime, timezone
from typing import Annotated, Generic, TypeVar

from bson import ObjectId
from pydantic import BaseModel, BeforeValidator, Field, model_validator

PyObjectId = Annotated[str, BeforeValidator(str)]

T = TypeVar("T")


def utc_now() -> str:
    """Return current UTC time as ISO string."""
    return datetime.now(timezone.utc).isoformat()


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated wrapper for list endpoints."""

    data: list[T]
    total: int = Field(description="Total number of matching documents")
    skip: int = Field(description="Number of documents skipped")
    limit: int = Field(description="Maximum documents returned")


class MongoBase(BaseModel):
    """Base model for all MongoDB documents."""

    id: PyObjectId | None = Field(
        default=None, serialization_alias="_id", description="MongoDB document ID"
    )
    created_at: str = Field(default_factory=utc_now)

    def model_dump_mongo(self) -> dict:
        """Dump model to a dict suitable for MongoDB insertion."""
        out = self.model_dump(by_alias=True)
        if "_id" in out and out["_id"]:
            out["_id"] = ObjectId(out["_id"])
        elif "_id" in out:
            del out["_id"]
        return out

    @model_validator(mode="before")
    @classmethod
    def validate_id(cls, values):
        if not values:
            return values
        if (
            isinstance(values, dict)
            and "_id" in values
            and isinstance(values["_id"], ObjectId)
        ):
            values["id"] = str(values.pop("_id"))
        return values


class StatusResponse(BaseModel):
    """Generic status response."""
    status: str = "ok"
    message: str = ""


# ── Shared mixins for historical / seeded documents ──────────────────────────

class SeasonScoped(BaseModel):
    """Common season/year fields shared by historical documents."""

    season_year: int = Field(description="Championship season year")


class RaceScoped(SeasonScoped):
    """Common race identity fields shared by round-level documents."""

    race_id: int = Field(description="Kaggle raceId")
    round: int = Field(description="Round number in the season")
    race_name: str = Field(description="Race name")


class CircuitIdentity(BaseModel):
    """Flat circuit reference fields used inside seeded documents."""

    circuit_id: int = Field(description="Kaggle circuitId")
    circuit_name: str = Field(default="", description="Circuit name")


class DriverIdentity(BaseModel):
    """Flat driver reference fields used inside seeded documents."""

    driver_id: int = Field(description="Kaggle driverId")
    driver_name: str = Field(description="Driver full name")


class ConstructorIdentity(BaseModel):
    """Flat constructor reference fields used inside seeded documents."""

    constructor_id: int = Field(description="Kaggle constructorId")
    constructor_name: str = Field(description="Constructor name")
