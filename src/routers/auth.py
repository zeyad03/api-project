"""Auth router – registration, login, token refresh, logout, profile."""

from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from src.config.settings import settings
from src.core.exceptions import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    UsernameAlreadyTakenError,
)
from src.core.rate_limit import limiter
from src.core.security import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    hash_password,
    verify_password,
)
from src.db.audit_logs import emit_audit_event
from src.db.tokens import (
    blacklist_access_token,
    revoke_all_user_tokens,
    revoke_refresh_token,
    store_refresh_token,
    validate_refresh_token,
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
from src.models.user import (
    LogoutRequest,
    RefreshRequest,
    Token,
    TokenData,
    User,
    UserCreate,
    UserUpdate,
    UserRole,
)

router = APIRouter()


# ── helpers ──────────────────────────────────────────────────────────────────
def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _user_agent(request: Request) -> str:
    return request.headers.get("user-agent", "unknown")


def _token_claims(user) -> dict:
    """Build the JWT claims dict for a user document / model."""
    return {
        "sub": user.username,
        "user_id": str(user.id),
        "role": user.role if isinstance(user.role, str) else user.role.value,
        "is_admin": user.is_admin,
    }


# ── Register ─────────────────────────────────────────────────────────────────
@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def register(body: UserCreate, request: Request):
    """Create a new user account and return access + refresh tokens."""
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
        "role": UserRole.USER.value,
        "is_admin": False,
        "created_at": utc_now(),
    }
    user = await create_user_db(user_doc, db)
    access = create_access_token(_token_claims(user))
    refresh = create_refresh_token()
    await store_refresh_token(refresh, str(user.id), db)

    await emit_audit_event(
        db,
        event_type="register",
        user_id=str(user.id),
        username=user.username,
        ip_address=_client_ip(request),
        user_agent=_user_agent(request),
    )
    return Token(access_token=access, refresh_token=refresh, user=user)


# ── Login ────────────────────────────────────────────────────────────────────
@router.post("/login", response_model=Token)
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def login(request: Request, form: OAuth2PasswordRequestForm = Depends()):
    """Authenticate with username & password and return access + refresh tokens."""
    db = request.app.state.db
    user_in_db = await get_user_by_username(form.username, db)
    if not user_in_db or not verify_password(form.password, user_in_db.password_hash):
        await emit_audit_event(
            db,
            event_type="login_failed",
            username=form.username,
            ip_address=_client_ip(request),
            user_agent=_user_agent(request),
            details={"reason": "invalid_credentials"},
        )
        raise InvalidCredentialsError()

    access = create_access_token(_token_claims(user_in_db))
    refresh = create_refresh_token()
    await store_refresh_token(refresh, str(user_in_db.id), db)

    await emit_audit_event(
        db,
        event_type="login",
        user_id=str(user_in_db.id),
        username=user_in_db.username,
        ip_address=_client_ip(request),
        user_agent=_user_agent(request),
    )
    user = User(**user_in_db.model_dump())
    return Token(access_token=access, refresh_token=refresh, user=user)


# ── Refresh token ────────────────────────────────────────────────────────────
@router.post("/refresh", response_model=Token)
@limiter.limit(settings.RATE_LIMIT_SENSITIVE)
async def refresh_token(body: RefreshRequest, request: Request):
    """Exchange a valid refresh token for a new access + refresh token pair.

    The old refresh token is revoked (token rotation).
    """
    db = request.app.state.db
    token_doc = await validate_refresh_token(body.refresh_token, db)
    if not token_doc:
        raise InvalidRefreshTokenError()

    # Revoke old refresh token (rotation)
    await revoke_refresh_token(body.refresh_token, db)

    # Fetch user and issue new pair
    user_in_db = await get_user_by_id(token_doc["user_id"], db)
    access = create_access_token(_token_claims(user_in_db))
    new_refresh = create_refresh_token()
    await store_refresh_token(new_refresh, str(user_in_db.id), db)

    await emit_audit_event(
        db,
        event_type="token_refresh",
        user_id=str(user_in_db.id),
        username=user_in_db.username,
        ip_address=_client_ip(request),
        user_agent=_user_agent(request),
    )
    user = User(**user_in_db.model_dump())
    return Token(access_token=access, refresh_token=new_refresh, user=user)


# ── Logout (single session) ─────────────────────────────────────────────────
@router.post("/logout", response_model=StatusResponse)
async def logout(
    body: LogoutRequest,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Revoke the supplied refresh token and blacklist the current access token."""
    db = request.app.state.db

    # Revoke refresh token
    await revoke_refresh_token(body.refresh_token, db)

    # Blacklist access token JTI so it can't be reused
    if current_user.jti:
        await blacklist_access_token(current_user.jti, current_user.exp, db)

    await emit_audit_event(
        db,
        event_type="logout",
        user_id=current_user.user_id,
        username=current_user.sub,
        ip_address=_client_ip(request),
        user_agent=_user_agent(request),
    )
    return StatusResponse(status="ok", message="Logged out successfully")


# ── Logout all sessions ─────────────────────────────────────────────────────
@router.post("/logout-all", response_model=StatusResponse)
async def logout_all(
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Revoke all refresh tokens for the current user (all devices)."""
    db = request.app.state.db

    revoked_count = await revoke_all_user_tokens(current_user.user_id, db)

    # Also blacklist the current access token
    if current_user.jti:
        await blacklist_access_token(current_user.jti, current_user.exp, db)

    await emit_audit_event(
        db,
        event_type="logout_all",
        user_id=current_user.user_id,
        username=current_user.sub,
        ip_address=_client_ip(request),
        user_agent=_user_agent(request),
        details={"revoked_sessions": revoked_count},
    )
    return StatusResponse(
        status="ok",
        message=f"Logged out of all sessions ({revoked_count} revoked)",
    )


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

    # Revoke all tokens for the user
    await revoke_all_user_tokens(current_user.user_id, db)

    await delete_user_db(current_user.user_id, db)

    await emit_audit_event(
        db,
        event_type="account_deleted",
        user_id=current_user.user_id,
        username=current_user.sub,
        ip_address=_client_ip(request),
        user_agent=_user_agent(request),
    )
    return StatusResponse(status="ok", message="Account deleted")
