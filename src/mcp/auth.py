"""MCP Bearer-token authentication helpers."""

from __future__ import annotations

from fastapi import Request

from src.config.settings import settings
from src.core.security import decode_token
from src.db.tokens import is_token_blacklisted
from src.models.user import TokenData

AUTH_REQUIRED_MESSAGE = "Authentication required for MCP tools"
INVALID_AUTH_HEADER_MESSAGE = "Invalid Authorization header. Use: Bearer <token>"
INVALID_TOKEN_MESSAGE = "Invalid authentication token"
TOKEN_REVOKED_MESSAGE = "This token has been revoked. Please log in again."


def extract_bearer_token(request: Request) -> str | None:
    """Return the raw token from an ``Authorization: Bearer …`` header.

    * ``None``  – no header present
    * ``""``    – header present but malformed
    * ``<tok>`` – extracted token string
    """
    auth_header = request.headers.get("authorization", "")
    if not auth_header:
        return None
    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return ""
    return token.strip()


async def authenticate_tool_call(
    request: Request,
) -> tuple[bool, str, TokenData | None]:
    """Check whether the incoming request is authorised to call MCP tools.

    Returns ``(ok, error_message, user)``.
    """
    if not settings.MCP_REQUIRE_AUTH:
        return True, "", None

    token = extract_bearer_token(request)
    if token is None:
        return False, AUTH_REQUIRED_MESSAGE, None
    if token == "":
        return False, INVALID_AUTH_HEADER_MESSAGE, None

    try:
        user = decode_token(token)
    except Exception:
        return False, INVALID_TOKEN_MESSAGE, None

    # Check JTI blacklist – revoked tokens must be rejected
    if user.jti:
        db = request.app.state.db
        if await is_token_blacklisted(user.jti, db):
            return False, TOKEN_REVOKED_MESSAGE, None

    return True, "", user
