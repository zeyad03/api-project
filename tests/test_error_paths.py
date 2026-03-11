"""Error-path tests – every HTTP error status the API can produce.

This module demonstrates *negative / boundary* testing by exercising
each error code the API is designed to return.  Tests are grouped by
HTTP status code so reviewers can confirm comprehensive coverage.

Categories covered:
  400 Bad Request          – malformed / incomplete request bodies
  401 Unauthorized         – missing or invalid credentials / tokens
  403 Forbidden            – valid auth but insufficient privileges
  404 Not Found            – referencing resources that do not exist
  409 Conflict             – duplicate usernames, emails, predictions
  422 Unprocessable Entity – schema-level validation failures
"""

import pytest
from unittest.mock import AsyncMock, patch

from src.core.exceptions import (
    DriverNotFoundError,
    DuplicateFavouriteItemError,
    DuplicatePredictionError,
    EmptyUpdateError,
    FavouriteListNotFoundError,
    HotTakeNotFoundError,
    PredictionNotFoundError,
    TeamNotFoundError,
)
from src.models.driver import Driver
from src.models.user import User, UserInDB

from .conftest import (
    FAKE_DRIVER_ID, FAKE_DRIVER2_ID, FAKE_FAV_ID, FAKE_FACT_ID,
    FAKE_PRED_ID, FAKE_TAKE_ID, FAKE_TEAM_ID, FAKE_USER_ID, TIMESTAMP,
)


# ── Factories ────────────────────────────────────────────────────────────────
def _user(**kw):
    defaults = dict(
        id=FAKE_USER_ID, username="testuser", email="test@example.com",
        display_name="Test User", role="user", is_admin=False,
        created_at=TIMESTAMP,
    )
    defaults.update(kw)
    return User(**defaults)


def _user_in_db(**kw):
    defaults = dict(
        id=FAKE_USER_ID, username="testuser", email="test@example.com",
        display_name="Test User", role="user", is_admin=False,
        password_hash="$2b$12$fakehash", created_at=TIMESTAMP,
    )
    defaults.update(kw)
    return UserInDB(**defaults)


def _driver(**kw):
    defaults = dict(
        id=FAKE_DRIVER_ID, name="Lewis Hamilton", number=44,
        team="Ferrari", nationality="British", active=True,
        created_at=TIMESTAMP,
    )
    defaults.update(kw)
    return Driver(**defaults)


# ═════════════════════════════════════════════════════════════════════════════
#  400 BAD REQUEST
# ═════════════════════════════════════════════════════════════════════════════
@pytest.mark.error_path
class TestBadRequest400:
    """Requests that are syntactically valid JSON but semantically wrong."""

    def test_h2h_vote_missing_winner(self, auth_client):
        """Voting without specifying a winner_id or winner_name → 400."""
        resp = auth_client.post("/head-to-head/vote", json={
            "driver1_id": FAKE_DRIVER_ID,
            "driver2_id": FAKE_DRIVER2_ID,
            # winner_id and winner_name both missing
        })
        assert resp.status_code == 400

    @patch("src.routers.auth.get_user_by_id", new_callable=AsyncMock)
    def test_get_me_user_deleted_underneath(self, mock_get, auth_client):
        """Token is valid but the user was deleted from DB → 404."""
        from src.core.exceptions import UserNotFoundError
        mock_get.side_effect = UserNotFoundError(FAKE_USER_ID)
        resp = auth_client.get("/auth/me")
        assert resp.status_code == 404

    @patch("src.routers.drivers.update_driver_db", new_callable=AsyncMock)
    def test_empty_patch_body_drivers(self, mock_update, admin_client):
        """PATCH with no updatable fields → 400 (EmptyUpdateError)."""
        mock_update.side_effect = EmptyUpdateError("driver")
        resp = admin_client.patch(f"/drivers/{FAKE_DRIVER_ID}", json={})
        assert resp.status_code == 400
        assert "No fields to update" in resp.json()["detail"]

    @patch("src.routers.teams.update_team_db", new_callable=AsyncMock)
    def test_empty_patch_body_teams(self, mock_update, admin_client):
        """PATCH with no updatable fields → 400 (EmptyUpdateError)."""
        mock_update.side_effect = EmptyUpdateError("team")
        resp = admin_client.patch(f"/teams/{FAKE_TEAM_ID}", json={})
        assert resp.status_code == 400


# ═════════════════════════════════════════════════════════════════════════════
#  401 UNAUTHORIZED
# ═════════════════════════════════════════════════════════════════════════════
@pytest.mark.error_path
class TestUnauthorized401:
    """Endpoints that require a valid Bearer token."""

    @pytest.mark.parametrize("method,url", [
        ("GET", "/auth/me"),
        ("PATCH", "/auth/me"),
        ("DELETE", "/auth/me"),
        ("POST", "/auth/logout"),
        ("POST", "/auth/logout-all"),
        ("GET", "/favourites"),
        ("POST", "/favourites"),
        ("GET", "/predictions"),
        ("POST", "/predictions"),
        ("POST", "/hot-takes"),
        ("POST", "/head-to-head/vote"),
    ])
    def test_protected_endpoint_rejects_anonymous(self, method, url, client):
        """Every protected endpoint must return 401 for anonymous users."""
        call = getattr(client, method.lower())
        # GET / DELETE don't accept a json kwarg; POST / PATCH do.
        if method in ("POST", "PATCH"):
            resp = call(url, json={})
        else:
            resp = call(url)
        assert resp.status_code == 401, f"{method} {url} did not return 401"

    @patch("src.routers.auth.get_user_by_username", new_callable=AsyncMock, return_value=None)
    @patch("src.routers.auth.emit_audit_event", new_callable=AsyncMock)
    def test_login_unknown_user(self, _audit, _gu, client):
        """Login with a username that doesn't exist → 401."""
        resp = client.post("/auth/login", data={
            "username": "ghost", "password": "irrelevant",
        })
        assert resp.status_code == 401

    @patch("src.routers.auth.verify_password", return_value=False)
    @patch("src.routers.auth.get_user_by_username", new_callable=AsyncMock)
    @patch("src.routers.auth.emit_audit_event", new_callable=AsyncMock)
    def test_login_wrong_password(self, _audit, mock_get, _vp, client):
        """Login with wrong password → 401."""
        mock_get.return_value = _user_in_db()
        resp = client.post("/auth/login", data={
            "username": "testuser", "password": "bad",
        })
        assert resp.status_code == 401

    @patch("src.routers.auth.validate_refresh_token", new_callable=AsyncMock,
           return_value=None)
    def test_refresh_with_invalid_token(self, _v, client):
        """Refresh with a revoked/invalid token → 401."""
        resp = client.post("/auth/refresh", json={"refresh_token": "bad-tok"})
        assert resp.status_code == 401


# ═════════════════════════════════════════════════════════════════════════════
#  403 FORBIDDEN
# ═════════════════════════════════════════════════════════════════════════════
@pytest.mark.error_path
class TestForbidden403:
    """Authenticated user lacks the required role / permission."""

    @pytest.mark.parametrize("method,url,body", [
        ("POST", "/drivers", {"name": "X", "number": 1, "team": "T"}),
        ("PATCH", f"/drivers/{FAKE_DRIVER_ID}", {"team": "Y"}),
        ("DELETE", f"/drivers/{FAKE_DRIVER_ID}", None),
        ("POST", "/teams", {"name": "X"}),
        ("PATCH", f"/teams/{FAKE_TEAM_ID}", {"name": "Y"}),
        ("DELETE", f"/teams/{FAKE_TEAM_ID}", None),
        ("PATCH", f"/trivia/{FAKE_FACT_ID}/approve", None),
        ("DELETE", f"/trivia/{FAKE_FACT_ID}", None),
    ])
    def test_regular_user_cannot_access_admin_endpoints(
        self, method, url, body, auth_client,
    ):
        """Non-admin users must receive 403 on admin-only routes."""
        kwargs = {"json": body} if body else {}
        resp = getattr(auth_client, method.lower())(url, **kwargs)
        assert resp.status_code == 403, f"{method} {url} did not return 403"


# ═════════════════════════════════════════════════════════════════════════════
#  404 NOT FOUND
# ═════════════════════════════════════════════════════════════════════════════
@pytest.mark.error_path
class TestNotFound404:
    """Requesting a resource that does not exist."""

    @patch("src.routers.drivers.get_driver_by_id", new_callable=AsyncMock)
    def test_driver_not_found(self, mock_get, client):
        mock_get.side_effect = DriverNotFoundError(FAKE_DRIVER_ID)
        resp = client.get(f"/drivers/{FAKE_DRIVER_ID}")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    @patch("src.routers.teams.get_team_by_id", new_callable=AsyncMock)
    def test_team_not_found(self, mock_get, client):
        mock_get.side_effect = TeamNotFoundError(FAKE_TEAM_ID)
        resp = client.get(f"/teams/{FAKE_TEAM_ID}")
        assert resp.status_code == 404

    @patch("src.routers.favourites.get_favourite_by_id", new_callable=AsyncMock)
    def test_favourite_not_found(self, mock_get, auth_client):
        mock_get.side_effect = FavouriteListNotFoundError(FAKE_FAV_ID)
        resp = auth_client.get(f"/favourites/{FAKE_FAV_ID}")
        assert resp.status_code == 404

    @patch("src.routers.hot_takes.get_hot_take_by_id", new_callable=AsyncMock)
    def test_hot_take_not_found(self, mock_get, client):
        mock_get.side_effect = HotTakeNotFoundError(FAKE_TAKE_ID)
        resp = client.get(f"/hot-takes/{FAKE_TAKE_ID}")
        assert resp.status_code == 404

    @patch("src.routers.predictions.get_prediction_by_id", new_callable=AsyncMock)
    def test_prediction_not_found(self, mock_get, auth_client):
        mock_get.side_effect = PredictionNotFoundError(FAKE_PRED_ID)
        resp = auth_client.get(f"/predictions/view/{FAKE_PRED_ID}")
        assert resp.status_code == 404

    @patch("src.routers.predictions.delete_prediction_db", new_callable=AsyncMock)
    def test_delete_prediction_not_found(self, mock_del, auth_client):
        mock_del.side_effect = PredictionNotFoundError(FAKE_PRED_ID)
        resp = auth_client.delete(f"/predictions/{FAKE_PRED_ID}")
        assert resp.status_code == 404

    @patch("src.routers.drivers.update_driver_db", new_callable=AsyncMock)
    def test_update_nonexistent_driver(self, mock_update, admin_client):
        mock_update.side_effect = DriverNotFoundError(FAKE_DRIVER_ID)
        resp = admin_client.patch(
            f"/drivers/{FAKE_DRIVER_ID}", json={"team": "Mercedes"},
        )
        assert resp.status_code == 404

    @patch("src.routers.teams.update_team_db", new_callable=AsyncMock)
    def test_update_nonexistent_team(self, mock_update, admin_client):
        mock_update.side_effect = TeamNotFoundError(FAKE_TEAM_ID)
        resp = admin_client.patch(
            f"/teams/{FAKE_TEAM_ID}", json={"name": "Ghost Racing"},
        )
        assert resp.status_code == 404

    @patch("src.routers.head_to_head.get_driver_by_name", new_callable=AsyncMock)
    def test_h2h_compare_unknown_driver(self, mock_drv, client):
        mock_drv.side_effect = DriverNotFoundError("nobody")
        resp = client.get("/head-to-head/compare/Nobody/Max%20Verstappen")
        assert resp.status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
#  409 CONFLICT
# ═════════════════════════════════════════════════════════════════════════════
@pytest.mark.error_path
class TestConflict409:
    """Duplicate or conflicting resource creation."""

    @patch("src.routers.auth.get_user_by_username", new_callable=AsyncMock)
    def test_register_duplicate_username(self, mock_get, client):
        mock_get.return_value = _user_in_db()
        resp = client.post("/auth/register", json={
            "username": "testuser", "email": "new@example.com",
            "display_name": "X", "password": "secret123",
        })
        assert resp.status_code == 409
        assert "username" in resp.json()["detail"].lower()

    @patch("src.routers.auth.get_user_by_email", new_callable=AsyncMock)
    @patch("src.routers.auth.get_user_by_username", new_callable=AsyncMock,
           return_value=None)
    def test_register_duplicate_email(self, _gu, mock_email, client):
        mock_email.return_value = _user_in_db()
        resp = client.post("/auth/register", json={
            "username": "newuser", "email": "test@example.com",
            "display_name": "X", "password": "secret123",
        })
        assert resp.status_code == 409
        assert "email" in resp.json()["detail"].lower()

    @patch("src.routers.predictions.create_prediction_db", new_callable=AsyncMock)
    def test_duplicate_prediction(self, mock_create, auth_client):
        mock_create.side_effect = DuplicatePredictionError(
            "driver_championship", 2025,
        )
        resp = auth_client.post("/predictions", json={
            "season": 2025, "category": "driver_championship",
            "predicted_id": FAKE_DRIVER_ID,
            "predicted_name": "Lewis Hamilton",
        })
        assert resp.status_code == 409

    @patch("src.routers.favourites.add_item_to_favourite", new_callable=AsyncMock)
    def test_duplicate_favourite_item(self, mock_add, auth_client):
        mock_add.side_effect = DuplicateFavouriteItemError("Hamilton")
        resp = auth_client.post(f"/favourites/{FAKE_FAV_ID}/items", json={
            "item_id": "d1", "name": "Hamilton",
        })
        assert resp.status_code == 409


# ═════════════════════════════════════════════════════════════════════════════
#  422 UNPROCESSABLE ENTITY (validation)
# ═════════════════════════════════════════════════════════════════════════════
@pytest.mark.error_path
class TestValidation422:
    """Schema-level validation failures caught by Pydantic / FastAPI."""

    def test_register_short_username(self, client):
        resp = client.post("/auth/register", json={
            "username": "ab", "email": "valid@email.com",
            "display_name": "Test", "password": "longenoughpassword",
        })
        assert resp.status_code == 422

    def test_register_invalid_email(self, client):
        resp = client.post("/auth/register", json={
            "username": "validuser", "email": "x",
            "display_name": "Test", "password": "secret123",
        })
        assert resp.status_code == 422

    def test_register_short_password(self, client):
        resp = client.post("/auth/register", json={
            "username": "validuser", "email": "a@b.com",
            "display_name": "Test", "password": "123",
        })
        assert resp.status_code == 422

    def test_register_empty_body(self, client):
        resp = client.post("/auth/register", json={})
        assert resp.status_code == 422

    def test_prediction_confidence_too_high(self, auth_client):
        resp = auth_client.post("/predictions", json={
            "season": 2025, "category": "driver_championship",
            "predicted_id": FAKE_DRIVER_ID,
            "predicted_name": "X", "confidence": 11,
        })
        assert resp.status_code == 422

    def test_prediction_invalid_category(self, auth_client):
        resp = auth_client.post("/predictions", json={
            "season": 2025, "category": "invalid_cat",
            "predicted_id": FAKE_DRIVER_ID,
            "predicted_name": "X",
        })
        assert resp.status_code == 422

    def test_hot_take_content_too_short(self, auth_client):
        resp = auth_client.post("/hot-takes", json={
            "content": "Short", "category": "general",
        })
        assert resp.status_code == 422

    def test_hot_take_invalid_category(self, auth_client):
        resp = auth_client.post("/hot-takes", json={
            "content": "A long enough hot take for testing.", "category": "nope",
        })
        assert resp.status_code == 422

    def test_favourite_invalid_list_type(self, auth_client):
        resp = auth_client.post("/favourites", json={
            "name": "Bad", "list_type": "invalid_type",
        })
        assert resp.status_code == 422

    def test_hot_take_invalid_reaction(self, auth_client):
        resp = auth_client.post(
            f"/hot-takes/{FAKE_TAKE_ID}/react", json={"reaction": "love"},
        )
        assert resp.status_code == 422

    def test_mcp_invalid_prediction_category(self, client):
        """MCP tool with an invalid category → JSON-RPC -32602."""
        resp = client.post("/mcp", json={
            "jsonrpc": "2.0", "id": 1,
            "method": "tools/call",
            "params": {
                "name": "get_prediction_leaderboard",
                "arguments": {"category": "invalid"},
            },
        })
        assert resp.json()["error"]["code"] == -32602
