"""F1 Team / Constructor model and season statistics."""

from pydantic import BaseModel, Field

from src.models.common import (
    ConstructorIdentity,
    MongoBase,
    RaceScoped,
    SeasonScoped,
)


class Team(MongoBase):
    """An F1 constructor / team."""
    name: str = Field(description="Short team name")
    full_name: str = Field(default="", description="Official registered name")
    base: str = Field(default="", description="Team headquarters location")
    team_principal: str = Field(default="")
    nationality: str = Field(default="")
    championships: int = Field(default=0)
    first_entry: int = Field(default=0, description="Year of first F1 entry")
    car: str = Field(default="", description="Current car model designation")
    engine: str = Field(default="", description="Engine / power unit supplier")
    active: bool = Field(default=True)
    kaggle_constructor_id: int = Field(default=0, description="Original Kaggle constructorId")
    constructor_ref: str = Field(default="", description="Kaggle constructorRef slug")


class TeamCreate(BaseModel):
    """Payload to create a new team."""
    name: str
    full_name: str = ""
    base: str = ""
    team_principal: str = ""
    nationality: str = ""
    championships: int = 0
    first_entry: int = 0
    car: str = ""
    engine: str = ""
    active: bool = True
    kaggle_constructor_id: int = 0
    constructor_ref: str = ""


class TeamUpdate(BaseModel):
    """Payload to update an existing team."""
    name: str | None = None
    full_name: str | None = None
    base: str | None = None
    team_principal: str | None = None
    nationality: str | None = None
    championships: int | None = None
    first_entry: int | None = None
    car: str | None = None
    engine: str | None = None
    active: bool | None = None
    kaggle_constructor_id: int | None = None
    constructor_ref: str | None = None


class ConstructorResult(MongoBase, RaceScoped, ConstructorIdentity):
    """Constructor race result from ``constructor_results.csv``."""

    constructor_result_id: int = Field(description="Kaggle constructorResultsId")
    points: float = Field(default=0.0)
    status: str = Field(default="")


class ConstructorStanding(MongoBase, RaceScoped, ConstructorIdentity):
    """Constructor standings snapshot from ``constructor_standings.csv``."""

    constructor_standing_id: int = Field(description="Kaggle constructorStandingsId")
    points: float = Field(default=0.0)
    position: int = Field(default=0)
    position_text: str = Field(default="")
    wins: int = Field(default=0)
    is_final_race: bool = Field(default=False)


class ConstructorSeasonStat(MongoBase, SeasonScoped, ConstructorIdentity):
    """Aggregated season performance for a constructor."""

    race_entries: int = Field(default=0)
    total_points: float = Field(default=0.0)
    wins: int = Field(default=0)
    podium_finishes: int = Field(default=0)
    championship_position: int = Field(default=0)
    champion: bool = Field(default=False)
