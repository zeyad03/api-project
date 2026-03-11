"""F1 Season model."""

from pydantic import Field

from src.models.common import MongoBase


class Season(MongoBase):
    """Season summary enriched with champion and calendar metadata."""

    year: int = Field(description="Championship season year")
    url: str = Field(default="")
    race_count: int = Field(default=0)
    sprint_round_count: int = Field(default=0)
    opening_race: str = Field(default="")
    final_race: str = Field(default="")
    champion_driver_id: int = Field(default=0)
    champion_driver_name: str = Field(default="")
    champion_constructor_id: int = Field(default=0)
    champion_constructor_name: str = Field(default="")
