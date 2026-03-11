"""User models for registration, authentication, and profile management."""

from enum import Enum

from pydantic import BaseModel, Field

from src.models.common import MongoBase, PyObjectId


# ── Role enum ────────────────────────────────────────────────────────────────
class UserRole(str, Enum):
    """Hierarchical user roles (user < moderator < admin)."""
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"


ROLE_HIERARCHY: dict[UserRole, int] = {
    UserRole.USER: 0,
    UserRole.MODERATOR: 1,
    UserRole.ADMIN: 2,
}


# ── Stored document ──────────────────────────────────────────────────────────
class User(MongoBase):
    """Public-facing user data (no password)."""
    username: str = Field(min_length=3, max_length=30)
    email: str = Field(min_length=5)
    display_name: str = Field(min_length=1, max_length=50)
    role: UserRole = UserRole.USER
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


class RefreshRequest(BaseModel):
    """Payload for refreshing an access token."""
    refresh_token: str


class LogoutRequest(BaseModel):
    """Payload for logout (revoke a specific refresh token)."""
    refresh_token: str


# ── Auth response schemas ────────────────────────────────────────────────────
class Token(BaseModel):
    """JWT token response returned on login / register."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: User


class TokenData(BaseModel):
    """Decoded JWT payload."""
    sub: str          # username
    user_id: str
    role: str = "user"
    is_admin: bool
    jti: str = ""
    exp: float
