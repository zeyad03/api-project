"""User models for registration, authentication, and profile management."""

from pydantic import BaseModel, Field

from src.models.common import MongoBase, PyObjectId


# ── Stored document ──────────────────────────────────────────────────────────
class User(MongoBase):
    """Public-facing user data (no password)."""
    username: str = Field(min_length=3, max_length=30)
    email: str = Field(min_length=5)
    display_name: str = Field(min_length=1, max_length=50)
    is_admin: bool = False


class UserInDB(User):
    """User as stored in MongoDB (includes hashed password)."""
    password_hash: str


# ── Request schemas ──────────────────────────────────────────────────────────
class UserCreate(BaseModel):
    """Payload for registering a new user."""
    username: str = Field(min_length=3, max_length=30)
    email: str = Field(min_length=5)
    display_name: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=6)


class UserUpdate(BaseModel):
    """Payload for updating profile fields."""
    display_name: str | None = None
    email: str | None = None


class UserLogin(BaseModel):
    """Payload for logging in."""
    username: str
    password: str


# ── Auth response schemas ────────────────────────────────────────────────────
class Token(BaseModel):
    """JWT token response returned on login."""
    access_token: str
    token_type: str = "bearer"
    user: User


class TokenData(BaseModel):
    """Decoded JWT payload."""
    sub: str          # username
    user_id: str
    is_admin: bool
    exp: float
