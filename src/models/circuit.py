"""F1 Circuit / venue model."""

from pydantic import Field

from src.models.common import MongoBase


class Circuit(MongoBase):
    """Stored circuit / venue information derived from ``circuits.csv``."""

    circuit_id: int = Field(description="Kaggle circuitId")
    circuit_ref: str = Field(default="", description="Kaggle circuitRef slug")
    name: str = Field(description="Circuit name")
    location: str = Field(default="")
    country: str = Field(default="")
    latitude: float = Field(default=0.0)
    longitude: float = Field(default=0.0)
    altitude: int = Field(default=0)
    url: str = Field(default="")
    race_count: int = Field(default=0)
    first_used_year: int = Field(default=0)
    last_used_year: int = Field(default=0)
    active: bool = Field(default=False)
