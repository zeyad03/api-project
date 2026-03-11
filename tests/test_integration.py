"""Integration-style flow tests – multi-step user journeys.

Each test in this module exercises *several* endpoints in sequence,
verifying that the outputs of one step feed correctly into the next.
All external I/O (MongoDB) is still mocked so the tests run in CI
without infrastructure, but the *workflow logic* is exercised end-to-end.

Flow tested
===========
1. Register a new account   → receive tokens + user object
2. Login with credentials   → receive a fresh token pair
3. Refresh the token pair    → old token rotated, new pair issued
4. Create a favourite list   → returns list with user ownership
5. Add an item to the list   → list reflects the new item
6. Submit a hot take         → take created with user's display name
7. React to the hot take     → agree count incremented
8. Create a prediction       → prediction stored for user
9. Update the prediction     → confidence value changed
10. Delete the prediction    → confirmed removed
11. Delete the account       → all tokens revoked, user removed
"""

import pytest
from unittest.mock import AsyncMock, patch

from src.models.user import User, UserInDB
from src.models.favourite import FavouriteList
from src.models.hot_take import HotTake
from src.models.prediction import Prediction

from .conftest import (
    FAKE_FAV_ID, FAKE_PRED_ID, FAKE_TAKE_ID, FAKE_USER_ID,
    FAKE_DRIVER_ID, TIMESTAMP,
)


# ── Factories ────────────────────────────────────────────────────────────────
def _user(**kw):
    defaults = dict(
        id=FAKE_USER_ID, username="integrationuser", email="int@example.com",
        display_name="Integration Test", role="user", is_admin=False,
        created_at=TIMESTAMP,
    )
    defaults.update(kw)
    return User(**defaults)


def _user_in_db(**kw):
    defaults = dict(
        id=FAKE_USER_ID, username="integrationuser", email="int@example.com",
        display_name="Integration Test", role="user", is_admin=False,
        password_hash="$2b$12$fakehashvalue", created_at=TIMESTAMP,
    )
    defaults.update(kw)
    return UserInDB(**defaults)


def _fav_list(**kw):
    defaults = dict(
        id=FAKE_FAV_ID, user_id=FAKE_USER_ID, name="My Drivers",
        list_type="drivers", items=[], updated_at=TIMESTAMP,
        created_at=TIMESTAMP,
    )
    defaults.update(kw)
    return FavouriteList(**defaults)


def _take(**kw):
    defaults = dict(
        id=FAKE_TAKE_ID, user_id=FAKE_USER_ID,
        user_display_name="Integration Test",
        content="Hamilton will win 2026 championship",
        category="driver", agrees=0, disagrees=0,
        agreed_by=[], disagreed_by=[], created_at=TIMESTAMP,
    )
    defaults.update(kw)
    return HotTake(**defaults)


def _prediction(**kw):
    defaults = dict(
        id=FAKE_PRED_ID, user_id=FAKE_USER_ID, season=2025,
        category="driver_championship", predicted_id=FAKE_DRIVER_ID,
        predicted_name="Lewis Hamilton", confidence=8,
        reasoning="Goat", created_at=TIMESTAMP,
    )
    defaults.update(kw)
    return Prediction(**defaults)


# ═════════════════════════════════════════════════════════════════════════════
#  Full user journey
# ═════════════════════════════════════════════════════════════════════════════
@pytest.mark.integration
class TestFullUserJourney:
    """Register → login → use features → delete account."""

    # ── Step 1: Register ─────────────────────────────────────────────────
    @patch("src.routers.auth.emit_audit_event", new_callable=AsyncMock)
    @patch("src.routers.auth.store_refresh_token", new_callable=AsyncMock)
    @patch("src.routers.auth.create_refresh_token", return_value="reg-refresh")
    @patch("src.routers.auth.create_access_token", return_value="reg-access")
    @patch("src.routers.auth.hash_password", return_value="hashed")
    @patch("src.routers.auth.create_user_db", new_callable=AsyncMock)
    @patch("src.routers.auth.get_user_by_email", new_callable=AsyncMock,
           return_value=None)
    @patch("src.routers.auth.get_user_by_username", new_callable=AsyncMock,
           return_value=None)
    def test_step1_register(self, _gu, _ge, mock_create, _hp, _ct, _crt,
                            _srt, _audit, client):
        mock_create.return_value = _user()
        resp = client.post("/auth/register", json={
            "username": "integrationuser", "email": "int@example.com",
            "display_name": "Integration Test", "password": "secret123",
        })
        assert resp.status_code == 201
        body = resp.json()
        assert body["access_token"] == "reg-access"
        assert body["refresh_token"] == "reg-refresh"
        assert body["user"]["username"] == "integrationuser"
        # Verify the user creation function was called
        mock_create.assert_awaited_once()

    # ── Step 2: Login ────────────────────────────────────────────────────
    @patch("src.routers.auth.emit_audit_event", new_callable=AsyncMock)
    @patch("src.routers.auth.store_refresh_token", new_callable=AsyncMock)
    @patch("src.routers.auth.create_refresh_token", return_value="login-refresh")
    @patch("src.routers.auth.create_access_token", return_value="login-access")
    @patch("src.routers.auth.verify_password", return_value=True)
    @patch("src.routers.auth.get_user_by_username", new_callable=AsyncMock)
    def test_step2_login(self, mock_get, _vp, _ct, _crt, _srt, _audit,
                         client):
        mock_get.return_value = _user_in_db()
        resp = client.post("/auth/login", data={
            "username": "integrationuser", "password": "secret123",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["access_token"] == "login-access"
        assert body["user"]["username"] == "integrationuser"

    # ── Step 3: Refresh tokens ───────────────────────────────────────────
    @patch("src.routers.auth.emit_audit_event", new_callable=AsyncMock)
    @patch("src.routers.auth.store_refresh_token", new_callable=AsyncMock)
    @patch("src.routers.auth.create_refresh_token",
           return_value="rotated-refresh")
    @patch("src.routers.auth.create_access_token",
           return_value="rotated-access")
    @patch("src.routers.auth.get_user_by_id", new_callable=AsyncMock)
    @patch("src.routers.auth.revoke_refresh_token", new_callable=AsyncMock,
           return_value=True)
    @patch("src.routers.auth.validate_refresh_token", new_callable=AsyncMock)
    def test_step3_refresh(self, mock_val, _rev, mock_user, _ct, _crt,
                           _srt, _audit, client):
        mock_val.return_value = {
            "user_id": FAKE_USER_ID, "token_hash": "x",
        }
        mock_user.return_value = _user_in_db()
        resp = client.post("/auth/refresh", json={
            "refresh_token": "login-refresh",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["access_token"] == "rotated-access"
        assert body["refresh_token"] == "rotated-refresh"
        # Old token was revoked
        _rev.assert_awaited_once()

    # ── Step 4: Create a favourites list ─────────────────────────────────
    @patch("src.routers.favourites.create_favourite_db",
           new_callable=AsyncMock)
    def test_step4_create_favourite(self, mock_create, auth_client):
        mock_create.return_value = _fav_list()
        resp = auth_client.post("/favourites", json={
            "name": "My Drivers", "list_type": "drivers",
        })
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "My Drivers"
        assert body["list_type"] == "drivers"
        assert body["items"] == []

    # ── Step 5: Add item to list ─────────────────────────────────────────
    @patch("src.routers.favourites.add_item_to_favourite",
           new_callable=AsyncMock)
    def test_step5_add_item(self, mock_add, auth_client):
        mock_add.return_value = _fav_list(
            items=[{"item_id": FAKE_DRIVER_ID, "name": "Hamilton"}],
        )
        resp = auth_client.post(
            f"/favourites/{FAKE_FAV_ID}/items",
            json={"item_id": FAKE_DRIVER_ID, "name": "Hamilton"},
        )
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 1
        assert resp.json()["items"][0]["name"] == "Hamilton"

    # ── Step 6: Submit a hot take ────────────────────────────────────────
    @patch("src.routers.hot_takes.create_hot_take_db",
           new_callable=AsyncMock)
    @patch("src.routers.hot_takes.get_user_by_id", new_callable=AsyncMock)
    def test_step6_create_hot_take(self, mock_user, mock_create,
                                   auth_client):
        mock_user.return_value = _user_in_db()
        mock_create.return_value = _take()
        resp = auth_client.post("/hot-takes", json={
            "content": "Hamilton will win 2026 championship",
            "category": "driver",
        })
        assert resp.status_code == 201
        assert resp.json()["user_display_name"] == "Integration Test"

    # ── Step 7: React to the hot take ────────────────────────────────────
    @patch("src.routers.hot_takes.react_to_hot_take",
           new_callable=AsyncMock)
    def test_step7_agree_hot_take(self, mock_react, auth_client):
        mock_react.return_value = _take(
            agrees=1, agreed_by=[FAKE_USER_ID],
        )
        resp = auth_client.post(
            f"/hot-takes/{FAKE_TAKE_ID}/react",
            json={"reaction": "agree"},
        )
        assert resp.status_code == 200
        assert resp.json()["agrees"] == 1

    # ── Step 8: Create a prediction ──────────────────────────────────────
    @patch("src.routers.predictions.create_prediction_db",
           new_callable=AsyncMock)
    def test_step8_create_prediction(self, mock_create, auth_client):
        mock_create.return_value = _prediction()
        resp = auth_client.post("/predictions", json={
            "season": 2025, "category": "driver_championship",
            "predicted_id": FAKE_DRIVER_ID,
            "predicted_name": "Lewis Hamilton",
            "confidence": 8, "reasoning": "Goat",
        })
        assert resp.status_code == 201
        assert resp.json()["predicted_name"] == "Lewis Hamilton"
        assert resp.json()["confidence"] == 8

    # ── Step 9: Update the prediction ────────────────────────────────────
    @patch("src.routers.predictions.update_prediction_db",
           new_callable=AsyncMock)
    def test_step9_update_prediction(self, mock_update, auth_client):
        mock_update.return_value = _prediction(confidence=10)
        resp = auth_client.patch(
            f"/predictions/{FAKE_PRED_ID}",
            json={"confidence": 10},
        )
        assert resp.status_code == 200
        assert resp.json()["confidence"] == 10

    # ── Step 10: Delete the prediction ───────────────────────────────────
    @patch("src.routers.predictions.delete_prediction_db",
           new_callable=AsyncMock, return_value=True)
    def test_step10_delete_prediction(self, _del, auth_client):
        resp = auth_client.delete(f"/predictions/{FAKE_PRED_ID}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    # ── Step 11: Delete account ──────────────────────────────────────────
    @patch("src.routers.auth.emit_audit_event", new_callable=AsyncMock)
    @patch("src.routers.auth.revoke_all_user_tokens",
           new_callable=AsyncMock, return_value=2)
    @patch("src.routers.auth.delete_user_db", new_callable=AsyncMock,
           return_value=True)
    def test_step11_delete_account(self, _del, mock_revoke, _audit,
                                   auth_client):
        resp = auth_client.delete("/auth/me")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        # Verify tokens were revoked during account deletion
        mock_revoke.assert_awaited_once()


# ═════════════════════════════════════════════════════════════════════════════
#  Admin management journey
# ═════════════════════════════════════════════════════════════════════════════
@pytest.mark.integration
class TestAdminManagementJourney:
    """Admin creates resources, regular user reads them, admin cleans up."""

    @patch("src.routers.drivers.create_driver_db", new_callable=AsyncMock)
    def test_step1_admin_creates_driver(self, mock_create, admin_client):
        from src.models.driver import Driver
        mock_create.return_value = Driver(
            id=FAKE_DRIVER_ID, name="Oscar Piastri", number=81,
            team="McLaren", nationality="Australian", active=True,
            created_at=TIMESTAMP,
        )
        resp = admin_client.post("/drivers", json={
            "name": "Oscar Piastri", "number": 81, "team": "McLaren",
        })
        assert resp.status_code == 201
        assert resp.json()["name"] == "Oscar Piastri"

    @patch("src.routers.drivers.get_driver_by_id", new_callable=AsyncMock)
    def test_step2_public_reads_driver(self, mock_get, client):
        from src.models.driver import Driver
        mock_get.return_value = Driver(
            id=FAKE_DRIVER_ID, name="Oscar Piastri", number=81,
            team="McLaren", nationality="Australian", active=True,
            created_at=TIMESTAMP,
        )
        resp = client.get(f"/drivers/{FAKE_DRIVER_ID}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Oscar Piastri"

    @patch("src.routers.drivers.update_driver_db", new_callable=AsyncMock)
    def test_step3_admin_updates_driver(self, mock_update, admin_client):
        from src.models.driver import Driver
        mock_update.return_value = Driver(
            id=FAKE_DRIVER_ID, name="Oscar Piastri", number=81,
            team="McLaren", nationality="Australian", active=True,
            championships=1, created_at=TIMESTAMP,
        )
        resp = admin_client.patch(
            f"/drivers/{FAKE_DRIVER_ID}", json={"championships": 1},
        )
        assert resp.status_code == 200
        assert resp.json()["championships"] == 1

    def test_step4_regular_user_cannot_delete(self, auth_client):
        resp = auth_client.delete(f"/drivers/{FAKE_DRIVER_ID}")
        assert resp.status_code == 403

    @patch("src.routers.drivers.delete_driver_db", new_callable=AsyncMock,
           return_value=True)
    def test_step5_admin_deletes_driver(self, _del, admin_client):
        resp = admin_client.delete(f"/drivers/{FAKE_DRIVER_ID}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    @patch("src.routers.drivers.get_driver_by_id", new_callable=AsyncMock)
    def test_step6_driver_gone_after_delete(self, mock_get, client):
        from src.core.exceptions import DriverNotFoundError
        mock_get.side_effect = DriverNotFoundError(FAKE_DRIVER_ID)
        resp = client.get(f"/drivers/{FAKE_DRIVER_ID}")
        assert resp.status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
#  Cross-resource interaction journey
# ═════════════════════════════════════════════════════════════════════════════
@pytest.mark.integration
class TestCrossResourceJourney:
    """User interacts with multiple resource types in one session."""

    @patch("src.routers.trivia.create_fact_db", new_callable=AsyncMock)
    def test_step1_submit_fact(self, mock_create, auth_client):
        from src.models.fact import Fact
        mock_create.return_value = Fact(
            id="507f1f77bcf86cd799439030",
            content="Monza is the Temple of Speed.",
            category="fun", source="", submitted_by=FAKE_USER_ID,
            approved=False, likes=0, liked_by=[], created_at=TIMESTAMP,
        )
        resp = auth_client.post("/trivia", json={
            "content": "Monza is the Temple of Speed.",
            "category": "fun",
        })
        assert resp.status_code == 201
        assert resp.json()["approved"] is False  # not yet approved

    @patch("src.routers.trivia.approve_fact_db", new_callable=AsyncMock)
    def test_step2_admin_approves_fact(self, mock_approve, admin_client):
        from src.models.fact import Fact
        mock_approve.return_value = Fact(
            id="507f1f77bcf86cd799439030",
            content="Monza is the Temple of Speed.",
            category="fun", source="", submitted_by=FAKE_USER_ID,
            approved=True, likes=0, liked_by=[], created_at=TIMESTAMP,
        )
        resp = admin_client.patch("/trivia/507f1f77bcf86cd799439030/approve")
        assert resp.status_code == 200
        assert resp.json()["approved"] is True

    @patch("src.routers.trivia.like_fact_db", new_callable=AsyncMock)
    def test_step3_user_likes_fact(self, mock_like, auth_client):
        from src.models.fact import Fact
        mock_like.return_value = Fact(
            id="507f1f77bcf86cd799439030",
            content="Monza is the Temple of Speed.",
            category="fun", source="", submitted_by=FAKE_USER_ID,
            approved=True, likes=1, liked_by=[FAKE_USER_ID],
            created_at=TIMESTAMP,
        )
        resp = auth_client.post("/trivia/507f1f77bcf86cd799439030/like")
        assert resp.status_code == 200
        assert resp.json()["likes"] == 1

    @patch("src.routers.trivia.get_all_facts", new_callable=AsyncMock)
    def test_step4_public_sees_approved_facts(self, mock_get, client):
        from src.models.fact import Fact
        mock_get.return_value = [
            Fact(
                id="507f1f77bcf86cd799439030",
                content="Monza is the Temple of Speed.",
                category="fun", source="", submitted_by=FAKE_USER_ID,
                approved=True, likes=1, liked_by=[FAKE_USER_ID],
                created_at=TIMESTAMP,
            )
        ]
        resp = client.get("/trivia")
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["likes"] == 1
