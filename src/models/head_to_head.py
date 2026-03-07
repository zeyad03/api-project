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
    """Payload to cast a head-to-head vote.

    Supply either driver IDs or driver names (or a mix). Names are resolved
    to IDs via a case-insensitive lookup.
    """
    driver1_id: str | None = Field(default=None, description="Driver 1 MongoDB ID")
    driver2_id: str | None = Field(default=None, description="Driver 2 MongoDB ID")
    winner_id: str | None = Field(default=None, description="Winner MongoDB ID")
    driver1_name: str | None = Field(default=None, description="Driver 1 name (resolved to ID)")
    driver2_name: str | None = Field(default=None, description="Driver 2 name (resolved to ID)")
    winner_name: str | None = Field(default=None, description="Winner name (resolved to ID)")


class HeadToHeadComparison(BaseModel):
    """Side-by-side stat comparison of two drivers."""
    driver1: dict
    driver2: dict
    community_votes: dict = Field(
        default_factory=dict,
        description="{'driver1_votes': N, 'driver2_votes': N, 'total': N}"
    )
