"""Auth router – registration, login, profile."""

from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from src.config.settings import settings
from src.core.exceptions import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    UsernameAlreadyTakenError,
)
from src.core.rate_limit import limiter
from src.core.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from src.db.users import (
    create_user_db,
    delete_user_db,
    get_user_by_id,
    get_user_by_username,
    get_user_by_email,
    update_user_db,
)
from src.models.common import StatusResponse, utc_now
from src.models.user import Token, TokenData, User, UserCreate, UserUpdate

router = APIRouter()


# ── Register ─────────────────────────────────────────────────────────────────
@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def register(body: UserCreate, request: Request):
    """Create a new user account and return a JWT token."""
    db = request.app.state.db

    # Check uniqueness
    if await get_user_by_username(body.username, db):
        raise UsernameAlreadyTakenError(body.username)
    if await get_user_by_email(body.email, db):
        raise EmailAlreadyRegisteredError(body.email)

    user_doc = {
        "username": body.username,
        "email": body.email,
        "display_name": body.display_name,
        "password_hash": hash_password(body.password),
        "is_admin": False,
        "created_at": utc_now(),
    }
    user = await create_user_db(user_doc, db)
    token = create_access_token(
        {"sub": user.username, "user_id": str(user.id), "is_admin": user.is_admin}
    )
    return Token(access_token=token, user=user)


# ── Login ────────────────────────────────────────────────────────────────────
@router.post("/login", response_model=Token)
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def login(request: Request, form: OAuth2PasswordRequestForm = Depends()):
    """Authenticate with username & password (form-data) and return a JWT token."""
    db = request.app.state.db
    user_in_db = await get_user_by_username(form.username, db)
    if not user_in_db or not verify_password(form.password, user_in_db.password_hash):
        raise InvalidCredentialsError()

    token = create_access_token(
        {"sub": user_in_db.username, "user_id": str(user_in_db.id), "is_admin": user_in_db.is_admin}
    )
    user = User(**user_in_db.model_dump())
    return Token(access_token=token, user=user)


# ── Get current user profile ────────────────────────────────────────────────
@router.get("/me", response_model=User)
async def get_me(
    request: Request, current_user: TokenData = Depends(get_current_user)
):
    """Return the authenticated user's profile."""
    db = request.app.state.db
    user = await get_user_by_id(current_user.user_id, db)
    return User(**user.model_dump())


# ── Update profile ───────────────────────────────────────────────────────────
@router.patch("/me", response_model=User)
async def update_me(
    body: UserUpdate,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Update the authenticated user's profile fields."""
    db = request.app.state.db
    return await update_user_db(current_user.user_id, body, db)


# ── Delete account ───────────────────────────────────────────────────────────
@router.delete("/me", response_model=StatusResponse)
async def delete_me(
    request: Request, current_user: TokenData = Depends(get_current_user)
):
    """Delete the authenticated user's account."""
    db = request.app.state.db
    await delete_user_db(current_user.user_id, db)
    return StatusResponse(status="ok", message="Account deleted")
