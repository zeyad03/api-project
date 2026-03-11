"""JWT authentication, password hashing, refresh tokens, and RBAC utilities."""

import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import bcrypt
from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from src.config.settings import settings
from src.core.exceptions import (
    AdminRequiredError,
    InsufficientRoleError,
    InvalidTokenError,
    TokenRevokedError,
)
from src.db.tokens import is_token_blacklisted
from src.models.user import ROLE_HIERARCHY, TokenData, UserRole

# ── Password hashing ────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ── JWT token helpers ────────────────────────────────────────────────────────
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def create_access_token(data: dict) -> str:
    """Create a short-lived JWT access token with a unique JTI."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.TOKEN_EXPIRY_MINUTES)
    to_encode["exp"] = expire.timestamp()
    to_encode["jti"] = uuid4().hex
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token() -> str:
    """Generate a cryptographically-random opaque refresh token."""
    return secrets.token_urlsafe(48)


def decode_token(token: str) -> TokenData:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return TokenData(**payload)
    except JWTError:
        raise InvalidTokenError()


# ── FastAPI dependencies ────────────────────────────────────────────────────
async def get_current_user(
    request: Request, token: str = Depends(oauth2_scheme)
) -> TokenData:
    """Dependency – returns the authenticated user's token data.

    Also checks the token-blacklist so revoked tokens are rejected.
    """
    user = decode_token(token)

    # Check JTI blacklist (revoked tokens)
    if user.jti:
        db = request.app.state.db
        if await is_token_blacklisted(user.jti, db):
            raise TokenRevokedError()

    return user


def require_admin(current_user: TokenData = Depends(get_current_user)) -> TokenData:
    """Dependency – raises 403 unless the user is an admin."""
    if not current_user.is_admin:
        raise AdminRequiredError()
    return current_user


def require_role(min_role: UserRole):
    """Dependency factory – returns a dependency that enforces a minimum role.

    Usage::

        @router.post("/moderate")
        async def moderate(user: TokenData = Depends(require_role(UserRole.MODERATOR))):
            ...
    """
    min_level = ROLE_HIERARCHY[min_role]

    async def _check(current_user: TokenData = Depends(get_current_user)) -> TokenData:
        user_role = UserRole(current_user.role)
        if ROLE_HIERARCHY[user_role] < min_level:
            raise InsufficientRoleError(min_role.value)
        return current_user

    return _check
