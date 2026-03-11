"""Shared fixtures for the F1 Facts API test suite.

Testing strategy
================
Tests are categorised with ``pytest.mark`` labels so each category can
be run in isolation (``pytest -m unit``, ``pytest -m api``, etc.).

  * **unit**        – Pure-logic tests (models, security utils, DB-layer
                      functions) that never touch a real HTTP server.
  * **api**         – FastAPI endpoint tests via ``TestClient``: send a
                      request, assert status code + response body.
  * **error_path**  – Negative / boundary tests covering every HTTP error
                      status the API can produce (400–422).
  * **auth**        – Authentication & authorisation: register, login,
                      token refresh, logout, RBAC guards.
  * **integration** – Multi-step workflows that exercise several
                      endpoints in sequence (register → use → cleanup).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from src.main import app
from src.core.rate_limit import limiter
from src.core.security import get_current_user, require_admin
from src.models.user import TokenData

# Disable rate limiting during tests so requests are never throttled
limiter.enabled = False

# ── Fake IDs (valid 24-char hex ObjectId strings) ───────────────────────────
FAKE_USER_ID = "507f1f77bcf86cd799439011"
FAKE_ADMIN_ID = "507f1f77bcf86cd799439012"
FAKE_DRIVER_ID = "507f1f77bcf86cd799439013"
FAKE_DRIVER2_ID = "507f1f77bcf86cd799439020"
FAKE_TEAM_ID = "507f1f77bcf86cd799439014"
FAKE_FAV_ID = "507f1f77bcf86cd799439015"
FAKE_FACT_ID = "507f1f77bcf86cd799439016"
FAKE_TAKE_ID = "507f1f77bcf86cd799439017"
FAKE_PRED_ID = "507f1f77bcf86cd799439018"
FAKE_VOTE_ID = "507f1f77bcf86cd799439019"
TIMESTAMP = "2025-01-01T00:00:00+00:00"


# ── Dependency override callables ───────────────────────────────────────────
def _regular_user():
    return TokenData(
        sub="testuser", user_id=FAKE_USER_ID, role="user",
        is_admin=False, jti="test-jti-regular", exp=9999999999.0,
    )


def _admin_user():
    return TokenData(
        sub="admin", user_id=FAKE_ADMIN_ID, role="admin",
        is_admin=True, jti="test-jti-admin", exp=9999999999.0,
    )


def _moderator_user():
    return TokenData(
        sub="moderator", user_id="507f1f77bcf86cd799439021", role="moderator",
        is_admin=False, jti="test-jti-mod", exp=9999999999.0,
    )


# ── Fixtures ─────────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def _clear_overrides():
    """Clear dependency overrides after every test to prevent leakage."""
    yield
    app.dependency_overrides.clear()


@pytest.fixture()
def client():
    """TestClient with a mocked MongoDB connection (unauthenticated)."""
    with patch("src.main.AsyncIOMotorClient") as mock_motor:
        mock_db = MagicMock()
        mock_db.command = AsyncMock(return_value={"ok": 1})
        # Every collection access returns a mock whose async methods work
        mock_collection = MagicMock()
        mock_collection.create_index = AsyncMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        mock_motor.return_value.get_database.return_value = mock_db
        with TestClient(app) as c:
            yield c


@pytest.fixture()
def auth_client(client):
    """TestClient authenticated as a *regular* user."""
    app.dependency_overrides[get_current_user] = _regular_user
    return client


@pytest.fixture()
def admin_client(client):
    """TestClient authenticated as an *admin* user."""
    app.dependency_overrides[get_current_user] = _admin_user
    return client


@pytest.fixture()
def moderator_client(client):
    """TestClient authenticated as a *moderator* user."""
    app.dependency_overrides[get_current_user] = _moderator_user
    return client
