"""F1 Driver model."""

from pydantic import BaseModel, Field

from src.models.common import MongoBase


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
