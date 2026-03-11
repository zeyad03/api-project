"""F1 Driver model and season statistics."""

from pydantic import BaseModel, Field

from src.models.common import (
    ConstructorIdentity,
    DriverIdentity,
    MongoBase,
    SeasonScoped,
)


class Driver(MongoBase):
    """An F1 driver."""
    name: str = Field(description="Full name")
    number: int = Field(description="Car number")
    team: str = Field(description="Current team name")
    nationality: str = Field(default="")
    date_of_birth: str = Field(default="")
    championships: int = Field(default=0)
    wins: int = Field(default=0)
    podiums: int = Field(default=0)
    poles: int = Field(default=0)
    bio: str = Field(default="")
    active: bool = Field(default=True)
    kaggle_driver_id: int = Field(default=0, description="Original Kaggle driverId")
    driver_ref: str = Field(default="", description="Kaggle driverRef slug")
    code: str = Field(default="", description="3-letter driver code when available")


class DriverCreate(BaseModel):
    """Payload to create a new driver."""
    name: str
    number: int
    team: str
    nationality: str = ""
    date_of_birth: str = ""
    championships: int = 0
    wins: int = 0
    podiums: int = 0
    poles: int = 0
    bio: str = ""
    active: bool = True
    kaggle_driver_id: int = 0
    driver_ref: str = ""
    code: str = ""


class DriverUpdate(BaseModel):
    """Payload to update an existing driver."""
    name: str | None = None
    number: int | None = None
    team: str | None = None
    nationality: str | None = None
    championships: int | None = None
    wins: int | None = None
    podiums: int | None = None
    poles: int | None = None
    bio: str | None = None
    active: bool | None = None
    kaggle_driver_id: int | None = None
    driver_ref: str | None = None
    code: str | None = None


class DriverSeasonStat(MongoBase, SeasonScoped, DriverIdentity, ConstructorIdentity):
    """Aggregated season performance for a driver."""

    starts: int = Field(default=0)
    wins: int = Field(default=0)
    podiums: int = Field(default=0)
    poles: int = Field(default=0)
    race_points: float = Field(default=0.0)
    sprint_points: float = Field(default=0.0)
    sprint_wins: int = Field(default=0)
    sprint_podiums: int = Field(default=0)
    classified_finishes: int = Field(default=0)
    dnfs: int = Field(default=0)
    best_finish: int = Field(default=0)
    championship_position: int = Field(default=0)
    champion: bool = Field(default=False)
    total_points: float = Field(default=0.0)
