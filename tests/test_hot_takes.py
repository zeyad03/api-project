"""Tests for /hot-takes endpoints."""

from unittest.mock import AsyncMock, patch

from src.core.exceptions import HotTakeNotFoundError
from src.models.hot_take import HotTake
from src.models.user import UserInDB

from .conftest import FAKE_TAKE_ID, FAKE_USER_ID, TIMESTAMP


def _take(**overrides):
    defaults = dict(
        id=FAKE_TAKE_ID, user_id=FAKE_USER_ID, user_display_name="Test User",
        content="Hamilton is overrated", category="driver",
        agrees=0, disagrees=0, agreed_by=[], disagreed_by=[],
        created_at=TIMESTAMP,
    )
    defaults.update(overrides)
    return HotTake(**defaults)


def _user_in_db():
    return UserInDB(
        id=FAKE_USER_ID, username="testuser", email="test@example.com",
        display_name="Test User", is_admin=False,
        password_hash="hashed", created_at=TIMESTAMP,
    )


# ── Public list / get ────────────────────────────────────────────────────────
class TestListHotTakes:
    @patch("src.routers.hot_takes.get_all_hot_takes", new_callable=AsyncMock)
    def test_list_all(self, mock_get, client):
        mock_get.return_value = [_take()]
        resp = client.get("/hot-takes")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    @patch("src.routers.hot_takes.get_all_hot_takes", new_callable=AsyncMock)
    def test_sort_by_spicy(self, mock_get, client):
        mock_get.return_value = [_take()]
        resp = client.get("/hot-takes?sort_by=spicy")
        assert resp.status_code == 200

    @patch("src.routers.hot_takes.get_all_hot_takes", new_callable=AsyncMock, return_value=[])
    def test_list_empty(self, _m, client):
        resp = client.get("/hot-takes")
        assert resp.status_code == 200
        assert resp.json() == []


class TestGetHotTake:
    @patch("src.routers.hot_takes.get_hot_take_by_id", new_callable=AsyncMock)
    def test_found(self, mock_get, client):
        mock_get.return_value = _take()
        resp = client.get(f"/hot-takes/{FAKE_TAKE_ID}")
        assert resp.status_code == 200
        assert "overrated" in resp.json()["content"]

    @patch("src.routers.hot_takes.get_hot_take_by_id", new_callable=AsyncMock)
    def test_not_found(self, mock_get, client):
        mock_get.side_effect = HotTakeNotFoundError(FAKE_TAKE_ID)
        resp = client.get(f"/hot-takes/{FAKE_TAKE_ID}")
        assert resp.status_code == 404


# ── Create hot take ──────────────────────────────────────────────────────────
class TestCreateHotTake:
    @patch("src.routers.hot_takes.create_hot_take_db", new_callable=AsyncMock)
    @patch("src.routers.hot_takes.get_user_by_id", new_callable=AsyncMock)
    def test_success(self, mock_user, mock_create, auth_client):
        mock_user.return_value = _user_in_db()
        mock_create.return_value = _take()
        resp = auth_client.post("/hot-takes", json={
            "content": "Hamilton is overrated", "category": "driver",
        })
        assert resp.status_code == 201
        assert resp.json()["content"] == "Hamilton is overrated"

    def test_unauthenticated(self, client):
        resp = client.post("/hot-takes", json={
            "content": "Hamilton is overrated", "category": "driver",
        })
        assert resp.status_code == 401

    def test_invalid_category(self, auth_client):
        resp = auth_client.post("/hot-takes", json={
            "content": "Some hot take text.", "category": "invalid_cat",
        })
        assert resp.status_code == 422

    def test_content_too_short(self, auth_client):
        resp = auth_client.post("/hot-takes", json={
            "content": "Short", "category": "general",
        })
        assert resp.status_code == 422


# ── React to hot take ────────────────────────────────────────────────────────
class TestReactHotTake:
    @patch("src.routers.hot_takes.react_to_hot_take", new_callable=AsyncMock)
    def test_agree(self, mock_react, auth_client):
        mock_react.return_value = _take(agrees=1, agreed_by=[FAKE_USER_ID])
        resp = auth_client.post(
            f"/hot-takes/{FAKE_TAKE_ID}/react", json={"reaction": "agree"}
        )
        assert resp.status_code == 200
        assert resp.json()["agrees"] == 1

    @patch("src.routers.hot_takes.react_to_hot_take", new_callable=AsyncMock)
    def test_disagree(self, mock_react, auth_client):
        mock_react.return_value = _take(disagrees=1, disagreed_by=[FAKE_USER_ID])
        resp = auth_client.post(
            f"/hot-takes/{FAKE_TAKE_ID}/react", json={"reaction": "disagree"}
        )
        assert resp.status_code == 200
        assert resp.json()["disagrees"] == 1

    def test_invalid_reaction(self, auth_client):
        resp = auth_client.post(
            f"/hot-takes/{FAKE_TAKE_ID}/react", json={"reaction": "love"}
        )
        assert resp.status_code == 422


# ── Delete hot take ──────────────────────────────────────────────────────────
class TestDeleteHotTake:
    @patch("src.routers.hot_takes.delete_hot_take_db", new_callable=AsyncMock, return_value=True)
    def test_owner_can_delete(self, _del, auth_client):
        resp = auth_client.delete(f"/hot-takes/{FAKE_TAKE_ID}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_unauthenticated(self, client):
        resp = client.delete(f"/hot-takes/{FAKE_TAKE_ID}")
        assert resp.status_code == 401
