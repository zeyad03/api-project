"""Tests for /auth endpoints – register, login, profile CRUD."""

from unittest.mock import AsyncMock, patch

from src.models.user import User, UserInDB

from .conftest import FAKE_USER_ID, TIMESTAMP


# ── Helpers ──────────────────────────────────────────────────────────────────
def _make_user(**overrides):
    defaults = dict(
        id=FAKE_USER_ID, username="testuser", email="test@example.com",
        display_name="Test User", is_admin=False, created_at=TIMESTAMP,
    )
    defaults.update(overrides)
    return User(**defaults)


def _make_user_in_db(**overrides):
    defaults = dict(
        id=FAKE_USER_ID, username="testuser", email="test@example.com",
        display_name="Test User", is_admin=False,
        password_hash="$2b$12$fakehashvalue", created_at=TIMESTAMP,
    )
    defaults.update(overrides)
    return UserInDB(**defaults)


# ── Register ─────────────────────────────────────────────────────────────────
class TestRegister:
    @patch("src.routers.auth.create_access_token", return_value="tok")
    @patch("src.routers.auth.hash_password", return_value="hashed")
    @patch("src.routers.auth.create_user_db", new_callable=AsyncMock)
    @patch("src.routers.auth.get_user_by_email", new_callable=AsyncMock, return_value=None)
    @patch("src.routers.auth.get_user_by_username", new_callable=AsyncMock, return_value=None)
    def test_success(self, _gu, _ge, mock_create, _hp, _ct, client):
        mock_create.return_value = _make_user()
        resp = client.post("/auth/register", json={
            "username": "testuser", "email": "test@example.com",
            "display_name": "Test User", "password": "secret123",
        })
        assert resp.status_code == 201
        body = resp.json()
        assert body["access_token"] == "tok"
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
    @patch("src.routers.auth.create_access_token", return_value="tok")
    @patch("src.routers.auth.verify_password", return_value=True)
    @patch("src.routers.auth.get_user_by_username", new_callable=AsyncMock)
    def test_success(self, mock_get, _vp, _ct, client):
        mock_get.return_value = _make_user_in_db()
        resp = client.post("/auth/login", data={
            "username": "testuser", "password": "secret123",
        })
        assert resp.status_code == 200
        assert resp.json()["access_token"] == "tok"
        assert resp.json()["user"]["username"] == "testuser"

    @patch("src.routers.auth.get_user_by_username", new_callable=AsyncMock, return_value=None)
    def test_unknown_user(self, _gu, client):
        resp = client.post("/auth/login", data={
            "username": "nobody", "password": "secret123",
        })
        assert resp.status_code == 401

    @patch("src.routers.auth.verify_password", return_value=False)
    @patch("src.routers.auth.get_user_by_username", new_callable=AsyncMock)
    def test_wrong_password(self, mock_get, _vp, client):
        mock_get.return_value = _make_user_in_db()
        resp = client.post("/auth/login", data={
            "username": "testuser", "password": "wrong",
        })
        assert resp.status_code == 401


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

    @patch("src.routers.auth.delete_user_db", new_callable=AsyncMock, return_value=True)
    def test_delete_me(self, _del, auth_client):
        resp = auth_client.delete("/auth/me")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
