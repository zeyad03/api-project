"""Head-to-head driver comparison models."""

from pydantic import BaseModel, Field

from src.models.common import MongoBase


class HeadToHeadVote(MongoBase):
    """A user's vote in a head-to-head driver matchup."""
    driver1_id: str
    driver2_id: str
    user_id: str
    winner_id: str = Field(description="Which driver the user voted for")


class HeadToHeadVoteCreate(BaseModel):
    """Payload to cast a head-to-head vote."""
    driver1_id: str
    driver2_id: str
    winner_id: str


class HeadToHeadComparison(BaseModel):
    """Side-by-side stat comparison of two drivers."""
    driver1: dict
    driver2: dict
    community_votes: dict = Field(
        default_factory=dict,
        description="{'driver1_votes': N, 'driver2_votes': N, 'total': N}"
    )
