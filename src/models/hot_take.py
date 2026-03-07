"""Hot takes – controversial F1 opinions users can post and vote on."""

from pydantic import BaseModel, Field

from src.models.common import MongoBase


class HotTake(MongoBase):
    """A controversial F1 opinion."""
    user_id: str
    user_display_name: str = ""
    content: str = Field(description="The hot take text")
    category: str = Field(
        default="general",
        description="general, driver, team, rule, prediction"
    )
    agrees: int = Field(default=0)
    disagrees: int = Field(default=0)
    agreed_by: list[str] = Field(default_factory=list)
    disagreed_by: list[str] = Field(default_factory=list)


class HotTakeCreate(BaseModel):
    """Payload to post a hot take."""
    content: str = Field(min_length=10, max_length=500)
    category: str = Field(
        default="general",
        pattern="^(general|driver|team|rule|prediction)$"
    )


class HotTakeReaction(BaseModel):
    """Payload to agree or disagree with a hot take."""
    reaction: str = Field(pattern="^(agree|disagree)$")
