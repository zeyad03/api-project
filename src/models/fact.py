"""F1 facts / trivia models."""

from pydantic import BaseModel, Field

from src.models.common import MongoBase


class Fact(MongoBase):
    """An F1 trivia fact."""
    content: str = Field(description="The fact text")
    category: str = Field(
        default="fun",
        description="Category: history, records, fun, technical, quiz"
    )
    source: str = Field(default="")
    submitted_by: str = Field(default="system", description="User ID or 'system'")
    approved: bool = Field(default=False)
    likes: int = Field(default=0)
    liked_by: list[str] = Field(default_factory=list, description="User IDs")


class FactCreate(BaseModel):
    """Payload to submit a new fact."""
    content: str = Field(min_length=10, max_length=1000)
    category: str = Field(
        default="fun",
        pattern="^(history|records|fun|technical)$"
    )
    source: str = Field(default="")


class QuizQuestion(BaseModel):
    """A multiple-choice quiz question served to the user."""
    question_id: str
    question: str
    options: list[str]
    category: str = "quiz"


class QuizAnswer(BaseModel):
    """User's answer to a quiz question."""
    question_id: str
    answer: str


class QuizResult(BaseModel):
    """Result after checking a quiz answer."""
    correct: bool
    correct_answer: str
    fun_fact: str = ""
