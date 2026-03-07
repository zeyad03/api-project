"""Shared base classes and utilities for all models."""

from datetime import datetime, timezone
from typing import Annotated

from bson import ObjectId
from pydantic import BaseModel, BeforeValidator, Field, model_validator

PyObjectId = Annotated[str, BeforeValidator(str)]


def utc_now() -> str:
    """Return current UTC time as ISO string."""
    return datetime.now(timezone.utc).isoformat()


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
