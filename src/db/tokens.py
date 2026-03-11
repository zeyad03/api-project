"""Refresh-token and access-token blacklist database operations."""

import hashlib
from datetime import datetime, timedelta, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from src.config.settings import settings
from src.db.collections import collections


def _hash_token(token: str) -> str:
    """SHA-256 hash so we never store raw refresh tokens."""
    return hashlib.sha256(token.encode()).hexdigest()


# ── Refresh tokens ──────────────────────────────────────────────────────────

async def store_refresh_token(
    token: str,
    user_id: str,
    db: AsyncIOMotorDatabase,
) -> None:
    """Persist a hashed refresh token with an expiry timestamp."""
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRY_DAYS
    )
    await db[collections.refresh_tokens].insert_one(
        {
            "token_hash": _hash_token(token),
            "user_id": user_id,
            "expires_at": expires_at.isoformat(),
            "revoked": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )


async def validate_refresh_token(
    token: str, db: AsyncIOMotorDatabase
) -> dict | None:
    """Return the token document if valid, else ``None``."""
    doc = await db[collections.refresh_tokens].find_one(
        {
            "token_hash": _hash_token(token),
            "revoked": False,
        }
    )
    if not doc:
        return None
    # Check expiry
    if datetime.fromisoformat(doc["expires_at"]) < datetime.now(timezone.utc):
        # Auto-revoke expired tokens
        await db[collections.refresh_tokens].update_one(
            {"_id": doc["_id"]}, {"$set": {"revoked": True}}
        )
        return None
    return doc


async def revoke_refresh_token(
    token: str, db: AsyncIOMotorDatabase
) -> bool:
    """Revoke a single refresh token.  Returns True if a token was found."""
    result = await db[collections.refresh_tokens].update_one(
        {"token_hash": _hash_token(token), "revoked": False},
        {"$set": {"revoked": True}},
    )
    return result.modified_count > 0


async def revoke_all_user_tokens(
    user_id: str, db: AsyncIOMotorDatabase
) -> int:
    """Revoke every refresh token belonging to a user (logout-all)."""
    result = await db[collections.refresh_tokens].update_many(
        {"user_id": user_id, "revoked": False},
        {"$set": {"revoked": True}},
    )
    return result.modified_count


# ── Access-token blacklist (JTI-based) ──────────────────────────────────────

async def blacklist_access_token(
    jti: str,
    expires_at: float,
    db: AsyncIOMotorDatabase,
) -> None:
    """Add a JTI to the blacklist so the access token cannot be reused."""
    await db[collections.token_blacklist].insert_one(
        {
            "jti": jti,
            "expires_at": datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )


async def is_token_blacklisted(
    jti: str, db: AsyncIOMotorDatabase
) -> bool:
    """Check whether an access token's JTI has been revoked."""
    doc = await db[collections.token_blacklist].find_one({"jti": jti})
    return doc is not None
