"""Audit-log database operations for security event tracking."""

from datetime import datetime, timezone
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from src.db.collections import collections


async def emit_audit_event(
    db: AsyncIOMotorDatabase,
    *,
    event_type: str,
    user_id: str | None = None,
    username: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Write a security audit event to the ``audit_logs`` collection.

    ``event_type`` should be one of:
        login, login_failed, register, logout, logout_all,
        token_refresh, token_revoked, role_change, account_deleted
    """
    await db[collections.audit_logs].insert_one(
        {
            "event_type": event_type,
            "user_id": user_id,
            "username": username,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "details": details or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )


async def get_audit_logs(
    db: AsyncIOMotorDatabase,
    *,
    user_id: str | None = None,
    event_type: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """Retrieve recent audit log entries, optionally filtered."""
    query: dict[str, Any] = {}
    if user_id:
        query["user_id"] = user_id
    if event_type:
        query["event_type"] = event_type
    cursor = (
        db[collections.audit_logs]
        .find(query)
        .sort("timestamp", -1)
        .limit(limit)
    )
    return [doc async for doc in cursor]
