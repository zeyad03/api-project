"""F1 Race and status models."""

from pydantic import Field

from src.models.common import MongoBase, SeasonScoped


class Race(MongoBase, SeasonScoped):
    """Race calendar entry enriched with winner and circuit metadata."""

    race_id: int = Field(description="Kaggle raceId")
    round: int = Field(description="Round number in the season")
    name: str = Field(description="Race name")
    circuit_id: int = Field(description="Kaggle circuitId")
    circuit_name: str = Field(default="")
    location: str = Field(default="")
    country: str = Field(default="")
    date: str = Field(default="")
    time: str = Field(default="")
    url: str = Field(default="")
    has_sprint: bool = Field(default=False)
    winner_driver_id: int = Field(default=0)
    winner_driver_name: str = Field(default="")
    winner_constructor_id: int = Field(default=0)
    winner_constructor_name: str = Field(default="")


class Status(MongoBase):
    """Race status / finish reason from ``status.csv``."""

    status_id: int = Field(description="Kaggle statusId")
    status: str = Field(description="Status text")
