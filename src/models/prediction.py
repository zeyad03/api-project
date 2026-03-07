"""Championship prediction models."""

from pydantic import BaseModel, Field

from src.models.common import MongoBase


class Prediction(MongoBase):
    """A user's prediction for a championship outcome."""
    user_id: str
    season: int = Field(description="Season year, e.g. 2025")
    category: str = Field(
        description="'driver_championship' or 'constructor_championship'"
    )
    predicted_id: str = Field(description="ID of the driver or team")
    predicted_name: str = Field(description="Name for quick display")
    confidence: int = Field(default=5, ge=1, le=10, description="1-10 confidence")
    reasoning: str = Field(default="", max_length=500)


class PredictionCreate(BaseModel):
    """Payload to submit a prediction."""
    season: int
    category: str = Field(pattern="^(driver_championship|constructor_championship)$")
    predicted_id: str
    predicted_name: str
    confidence: int = Field(default=5, ge=1, le=10)
    reasoning: str = Field(default="", max_length=500)


class PredictionUpdate(BaseModel):
    """Payload to update an existing prediction."""
    predicted_id: str | None = None
    predicted_name: str | None = None
    confidence: int | None = Field(default=None, ge=1, le=10)
    reasoning: str | None = Field(default=None, max_length=500)


class LeaderboardEntry(BaseModel):
    """Aggregated prediction count for a driver/team."""
    predicted_id: str
    predicted_name: str
    vote_count: int
    avg_confidence: float
