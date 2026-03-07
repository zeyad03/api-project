"""Favourite lists – users can curate lists of drivers and teams."""

from pydantic import BaseModel, Field

from src.models.common import MongoBase, utc_now


class FavouriteItem(BaseModel):
    """A single item inside a favourite list."""
    item_id: str = Field(description="Driver or Team document ID")
    name: str = Field(description="Display name for quick reference")


class FavouriteList(MongoBase):
    """A named list of favourite drivers or teams belonging to a user."""
    user_id: str
    name: str = Field(min_length=1, max_length=100, description="List title")
    list_type: str = Field(description="Either 'drivers' or 'teams'")
    items: list[FavouriteItem] = []
    updated_at: str = Field(default_factory=utc_now)


class FavouriteListCreate(BaseModel):
    """Payload to create a favourite list."""
    name: str = Field(min_length=1, max_length=100)
    list_type: str = Field(pattern="^(drivers|teams)$")


class FavouriteListUpdate(BaseModel):
    """Payload to rename a favourite list."""
    name: str | None = Field(default=None, min_length=1, max_length=100)


class AddFavouriteItem(BaseModel):
    """Payload to add an item to a favourite list."""
    item_id: str
    name: str
