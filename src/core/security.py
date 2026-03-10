"""JWT authentication and password hashing utilities."""

from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from src.config.settings import settings
from src.core.exceptions import AdminRequiredError, InvalidTokenError
from src.models.user import TokenData

# ── Password hashing ────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ── JWT token helpers ────────────────────────────────────────────────────────
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.TOKEN_EXPIRY_MINUTES)
    to_encode["exp"] = expire.timestamp()
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> TokenData:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return TokenData(**payload)
    except JWTError:
        raise InvalidTokenError()


# ── FastAPI dependencies ────────────────────────────────────────────────────
def get_current_user(
    request: Request, token: str = Depends(oauth2_scheme)
) -> TokenData:
    """Dependency – returns the authenticated user's token data."""
    user = decode_token(token)
    return user


def require_admin(current_user: TokenData = Depends(get_current_user)) -> TokenData:
    """Dependency – raises 403 unless the user is an admin."""
    if not current_user.is_admin:
        raise AdminRequiredError()
    return current_user
