"""Tests for /auth endpoints – register, login, refresh, logout, profile CRUD."""

from unittest.mock import AsyncMock, patch

from src.models.user import User, UserInDB

from .conftest import FAKE_USER_ID, TIMESTAMP


# ── Helpers ──────────────────────────────────────────────────────────────────
def _make_user(**overrides):
    defaults = dict(
        id=FAKE_USER_ID, username="testuser", email="test@example.com",
        display_name="Test User", role="user", is_admin=False, created_at=TIMESTAMP,
    )
    defaults.update(overrides)
    return User(**defaults)


def _make_user_in_db(**overrides):
    defaults = dict(
        id=FAKE_USER_ID, username="testuser", email="test@example.com",
        display_name="Test User", role="user", is_admin=False,
        password_hash="$2b$12$fakehashvalue", created_at=TIMESTAMP,
    )
    defaults.update(overrides)
    return UserInDB(**defaults)


# ── Register ─────────────────────────────────────────────────────────────────
class TestRegister:
    @patch("src.routers.auth.emit_audit_event", new_callable=AsyncMock)
    @patch("src.routers.auth.store_refresh_token", new_callable=AsyncMock)
    @patch("src.routers.auth.create_refresh_token", return_value="refresh-tok")
    @patch("src.routers.auth.create_access_token", return_value="tok")
    @patch("src.routers.auth.hash_password", return_value="hashed")
    @patch("src.routers.auth.create_user_db", new_callable=AsyncMock)
    @patch("src.routers.auth.get_user_by_email", new_callable=AsyncMock, return_value=None)
    @patch("src.routers.auth.get_user_by_username", new_callable=AsyncMock, return_value=None)
    def test_success(self, _gu, _ge, mock_create, _hp, _ct, _crt, _srt, _audit, client):
        mock_create.return_value = _make_user()
        resp = client.post("/auth/register", json={
            "username": "testuser", "email": "test@example.com",
            "display_name": "Test User", "password": "secret123",
        })
        assert resp.status_code == 201
        body = resp.json()
        assert body["access_token"] == "tok"
        assert body["refresh_token"] == "refresh-tok"
        assert body["token_type"] == "bearer"
        assert body["user"]["username"] == "testuser"

    @patch("src.routers.auth.get_user_by_username", new_callable=AsyncMock)
    def test_duplicate_username(self, mock_get, client):
        mock_get.return_value = _make_user_in_db()
        resp = client.post("/auth/register", json={
            "username": "testuser", "email": "new@example.com",
            "display_name": "X", "password": "secret123",
        })
        assert resp.status_code == 409

    @patch("src.routers.auth.get_user_by_email", new_callable=AsyncMock)
    @patch("src.routers.auth.get_user_by_username", new_callable=AsyncMock, return_value=None)
    def test_duplicate_email(self, _gu, mock_email, client):
        mock_email.return_value = _make_user_in_db()
        resp = client.post("/auth/register", json={
            "username": "newuser", "email": "test@example.com",
            "display_name": "X", "password": "secret123",
        })
        assert resp.status_code == 409

    def test_invalid_payload(self, client):
        resp = client.post("/auth/register", json={
            "username": "ab", "email": "x", "display_name": "", "password": "123",
        })
        assert resp.status_code == 422


# ── Login ────────────────────────────────────────────────────────────────────
class TestLogin:
    @patch("src.routers.auth.emit_audit_event", new_callable=AsyncMock)
    @patch("src.routers.auth.store_refresh_token", new_callable=AsyncMock)
    @patch("src.routers.auth.create_refresh_token", return_value="refresh-tok")
    @patch("src.routers.auth.create_access_token", return_value="tok")
    @patch("src.routers.auth.verify_password", return_value=True)
    @patch("src.routers.auth.get_user_by_username", new_callable=AsyncMock)
    def test_success(self, mock_get, _vp, _ct, _crt, _srt, _audit, client):
        mock_get.return_value = _make_user_in_db()
        resp = client.post("/auth/login", data={
            "username": "testuser", "password": "secret123",
        })
        assert resp.status_code == 200
        assert resp.json()["access_token"] == "tok"
        assert resp.json()["refresh_token"] == "refresh-tok"
        assert resp.json()["user"]["username"] == "testuser"

    @patch("src.routers.auth.emit_audit_event", new_callable=AsyncMock)
    @patch("src.routers.auth.get_user_by_username", new_callable=AsyncMock, return_value=None)
    def test_unknown_user(self, _gu, _audit, client):
        resp = client.post("/auth/login", data={
            "username": "nobody", "password": "secret123",
        })
        assert resp.status_code == 401

    @patch("src.routers.auth.emit_audit_event", new_callable=AsyncMock)
    @patch("src.routers.auth.verify_password", return_value=False)
    @patch("src.routers.auth.get_user_by_username", new_callable=AsyncMock)
    def test_wrong_password(self, mock_get, _vp, _audit, client):
        mock_get.return_value = _make_user_in_db()
        resp = client.post("/auth/login", data={
            "username": "testuser", "password": "wrong",
        })
        assert resp.status_code == 401


# ── Refresh ──────────────────────────────────────────────────────────────────
class TestRefresh:
    @patch("src.routers.auth.emit_audit_event", new_callable=AsyncMock)
    @patch("src.routers.auth.store_refresh_token", new_callable=AsyncMock)
    @patch("src.routers.auth.create_refresh_token", return_value="new-refresh")
    @patch("src.routers.auth.create_access_token", return_value="new-access")
    @patch("src.routers.auth.get_user_by_id", new_callable=AsyncMock)
    @patch("src.routers.auth.revoke_refresh_token", new_callable=AsyncMock, return_value=True)
    @patch("src.routers.auth.validate_refresh_token", new_callable=AsyncMock)
    def test_success(self, mock_validate, _revoke, mock_user, _cat, _crt, _srt, _audit, client):
        mock_validate.return_value = {"user_id": FAKE_USER_ID, "token_hash": "x"}
        mock_user.return_value = _make_user_in_db()
        resp = client.post("/auth/refresh", json={"refresh_token": "old-refresh"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["access_token"] == "new-access"
        assert body["refresh_token"] == "new-refresh"

    @patch("src.routers.auth.validate_refresh_token", new_callable=AsyncMock, return_value=None)
    def test_invalid_refresh_token(self, _v, client):
        resp = client.post("/auth/refresh", json={"refresh_token": "bad-token"})
        assert resp.status_code == 401


# ── Logout ───────────────────────────────────────────────────────────────────
class TestLogout:
    @patch("src.routers.auth.emit_audit_event", new_callable=AsyncMock)
    @patch("src.routers.auth.blacklist_access_token", new_callable=AsyncMock)
    @patch("src.routers.auth.revoke_refresh_token", new_callable=AsyncMock, return_value=True)
    def test_logout(self, _revoke, _bl, _audit, auth_client):
        resp = auth_client.post("/auth/logout", json={"refresh_token": "some-tok"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    @patch("src.routers.auth.emit_audit_event", new_callable=AsyncMock)
    @patch("src.routers.auth.blacklist_access_token", new_callable=AsyncMock)
    @patch("src.routers.auth.revoke_all_user_tokens", new_callable=AsyncMock, return_value=3)
    def test_logout_all(self, _revoke_all, _bl, _audit, auth_client):
        resp = auth_client.post("/auth/logout-all")
        assert resp.status_code == 200
        assert "3 revoked" in resp.json()["message"]


# ── Profile ──────────────────────────────────────────────────────────────────
class TestProfile:
    @patch("src.routers.auth.get_user_by_id", new_callable=AsyncMock)
    def test_get_me(self, mock_get, auth_client):
        mock_get.return_value = _make_user_in_db()
        resp = auth_client.get("/auth/me")
        assert resp.status_code == 200
        assert resp.json()["username"] == "testuser"

    def test_get_me_unauthenticated(self, client):
        resp = client.get("/auth/me")
        assert resp.status_code == 401

    @patch("src.routers.auth.update_user_db", new_callable=AsyncMock)
    def test_update_me(self, mock_update, auth_client):
        mock_update.return_value = _make_user(display_name="New Name")
        resp = auth_client.patch("/auth/me", json={"display_name": "New Name"})
        assert resp.status_code == 200
        assert resp.json()["display_name"] == "New Name"

    @patch("src.routers.auth.emit_audit_event", new_callable=AsyncMock)
    @patch("src.routers.auth.revoke_all_user_tokens", new_callable=AsyncMock, return_value=0)
    @patch("src.routers.auth.delete_user_db", new_callable=AsyncMock, return_value=True)
    def test_delete_me(self, _del, _revoke, _audit, auth_client):
        resp = auth_client.delete("/auth/me")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
