"""F1 Race / sprint result and lap-time models."""

from pydantic import Field

from src.models.common import (
    CircuitIdentity,
    ConstructorIdentity,
    DriverIdentity,
    MongoBase,
    RaceScoped,
)


class ResultBase(MongoBase, RaceScoped, DriverIdentity, ConstructorIdentity):
    """Shared flat structure for race and sprint result documents."""

    result_id: int = Field(description="Native Kaggle result identifier")
    grid: int = Field(default=0)
    position: int = Field(default=0)
    position_text: str = Field(default="")
    position_order: int = Field(default=0)
    points: float = Field(default=0.0)
    laps: int = Field(default=0)
    time: str = Field(default="")
    milliseconds: int = Field(default=0)
    status_id: int = Field(default=0)
    status: str = Field(default="")
    classified_finish: bool = Field(default=False)


class RaceResult(ResultBase, CircuitIdentity):
    """Full grand prix result row derived from ``results.csv``."""

    number: int = Field(default=0)
    fastest_lap: int = Field(default=0)
    fastest_lap_time: str = Field(default="")
    fastest_lap_speed: float = Field(default=0.0)


class SprintResult(ResultBase):
    """Sprint result row derived from ``sprint_results.csv``."""

    fastest_lap: int = Field(default=0)
    fastest_lap_time: str = Field(default="")


class LapTimeSummary(MongoBase, RaceScoped, DriverIdentity, ConstructorIdentity):
    """Compact lap-time analytics derived from ``lap_times.csv``."""

    lap_count: int = Field(default=0)
    best_lap_time_ms: int = Field(default=0)
    best_lap_number: int = Field(default=0)
    average_lap_time_ms: float = Field(default=0.0)
    total_lap_time_ms: int = Field(default=0)
