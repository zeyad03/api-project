"""Tests for /favourites endpoints.

Category: **api** – HTTP request → response tests via TestClient.
"""

import pytest
from unittest.mock import AsyncMock, patch

from src.core.exceptions import FavouriteListNotFoundError
from src.models.favourite import FavouriteList

from .conftest import FAKE_FAV_ID, FAKE_USER_ID, TIMESTAMP

pytestmark = pytest.mark.api


def _fav_list(**overrides):
    defaults = dict(
        id=FAKE_FAV_ID, user_id=FAKE_USER_ID, name="My Top Drivers",
        list_type="drivers", items=[], updated_at=TIMESTAMP, created_at=TIMESTAMP,
    )
    defaults.update(overrides)
    return FavouriteList(**defaults)


# ── List favourites ──────────────────────────────────────────────────────────
class TestListFavourites:
    @patch("src.routers.favourites.get_user_favourites", new_callable=AsyncMock)
    def test_list_all(self, mock_get, auth_client):
        mock_get.return_value = [_fav_list()]
        resp = auth_client.get("/favourites")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    @patch("src.routers.favourites.get_user_favourites", new_callable=AsyncMock)
    def test_filter_by_type(self, mock_get, auth_client):
        mock_get.return_value = [_fav_list()]
        resp = auth_client.get("/favourites?list_type=drivers")
        assert resp.status_code == 200

    def test_unauthenticated(self, client):
        resp = client.get("/favourites")
        assert resp.status_code == 401


# ── Get single favourite ─────────────────────────────────────────────────────
class TestGetFavourite:
    @patch("src.routers.favourites.get_favourite_by_id", new_callable=AsyncMock)
    def test_found(self, mock_get, auth_client):
        mock_get.return_value = _fav_list()
        resp = auth_client.get(f"/favourites/{FAKE_FAV_ID}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "My Top Drivers"

    @patch("src.routers.favourites.get_favourite_by_id", new_callable=AsyncMock)
    def test_not_found(self, mock_get, auth_client):
        mock_get.side_effect = FavouriteListNotFoundError(FAKE_FAV_ID)
        resp = auth_client.get(f"/favourites/{FAKE_FAV_ID}")
        assert resp.status_code == 404


# ── Create favourite ─────────────────────────────────────────────────────────
class TestCreateFavourite:
    @patch("src.routers.favourites.create_favourite_db", new_callable=AsyncMock)
    def test_success(self, mock_create, auth_client):
        mock_create.return_value = _fav_list()
        resp = auth_client.post("/favourites", json={
            "name": "My Top Drivers", "list_type": "drivers",
        })
        assert resp.status_code == 201
        assert resp.json()["name"] == "My Top Drivers"

    def test_invalid_list_type(self, auth_client):
        resp = auth_client.post("/favourites", json={
            "name": "Bad", "list_type": "invalid",
        })
        assert resp.status_code == 422


# ── Update favourite ─────────────────────────────────────────────────────────
class TestUpdateFavourite:
    @patch("src.routers.favourites.update_favourite_db", new_callable=AsyncMock)
    def test_rename(self, mock_update, auth_client):
        mock_update.return_value = _fav_list(name="Renamed")
        resp = auth_client.patch(f"/favourites/{FAKE_FAV_ID}", json={"name": "Renamed"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "Renamed"


# ── Delete favourite ─────────────────────────────────────────────────────────
class TestDeleteFavourite:
    @patch("src.routers.favourites.delete_favourite_db", new_callable=AsyncMock, return_value=True)
    def test_success(self, _del, auth_client):
        resp = auth_client.delete(f"/favourites/{FAKE_FAV_ID}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


# ── Add / remove items ──────────────────────────────────────────────────────
class TestFavouriteItems:
    @patch("src.routers.favourites.add_item_to_favourite", new_callable=AsyncMock)
    def test_add_item(self, mock_add, auth_client):
        mock_add.return_value = _fav_list(items=[{"item_id": "d1", "name": "Hamilton"}])
        resp = auth_client.post(f"/favourites/{FAKE_FAV_ID}/items", json={
            "item_id": "d1", "name": "Hamilton",
        })
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 1

    @patch("src.routers.favourites.remove_item_from_favourite", new_callable=AsyncMock)
    def test_remove_item(self, mock_rm, auth_client):
        mock_rm.return_value = _fav_list(items=[])
        resp = auth_client.delete(f"/favourites/{FAKE_FAV_ID}/items/d1")
        assert resp.status_code == 200
        assert resp.json()["items"] == []
