"""F1 Team / Constructor model."""

from pydantic import BaseModel, Field

from src.models.common import MongoBase


class Team(MongoBase):
    """An F1 constructor / team."""
    name: str = Field(description="Short team name")
    full_name: str = Field(default="", description="Official registered name")
    base: str = Field(default="", description="Team headquarters location")
    team_principal: str = Field(default="")
    championships: int = Field(default=0)
    first_entry: int = Field(default=0, description="Year of first F1 entry")
    car: str = Field(default="", description="Current car model designation")
    engine: str = Field(default="", description="Engine / power unit supplier")
    active: bool = Field(default=True)


class TeamCreate(BaseModel):
    """Payload to create a new team."""
    name: str
    full_name: str = ""
    base: str = ""
    team_principal: str = ""
    championships: int = 0
    first_entry: int = 0
    car: str = ""
    engine: str = ""
    active: bool = True


class TeamUpdate(BaseModel):
    """Payload to update an existing team."""
    name: str | None = None
    full_name: str | None = None
    base: str | None = None
    team_principal: str | None = None
    championships: int | None = None
    first_entry: int | None = None
    car: str | None = None
    engine: str | None = None
    active: bool | None = None
