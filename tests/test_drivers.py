"""Tests for /drivers endpoints."""

from unittest.mock import AsyncMock, patch

from src.models.driver import Driver

from .conftest import FAKE_DRIVER_ID, TIMESTAMP


def _driver(**overrides):
    defaults = dict(
        id=FAKE_DRIVER_ID, name="Lewis Hamilton", number=44,
        team="Ferrari", nationality="British", date_of_birth="1985-01-07",
        championships=7, wins=103, podiums=197, poles=104,
        bio="", active=True, created_at=TIMESTAMP,
    )
    defaults.update(overrides)
    return Driver(**defaults)


# ── Public endpoints ─────────────────────────────────────────────────────────
class TestListDrivers:
    @patch("src.routers.drivers.get_all_drivers", new_callable=AsyncMock)
    def test_list_all(self, mock_get, client):
        mock_get.return_value = [_driver()]
        resp = client.get("/drivers")
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["name"] == "Lewis Hamilton"

    @patch("src.routers.drivers.get_all_drivers", new_callable=AsyncMock)
    def test_list_active_only(self, mock_get, client):
        mock_get.return_value = [_driver()]
        resp = client.get("/drivers?active_only=true")
        assert resp.status_code == 200
        mock_get.assert_awaited_once()
        call_kwargs = mock_get.call_args
        assert call_kwargs[1].get("active_only") is True or call_kwargs[0][1] is True

    @patch("src.routers.drivers.get_all_drivers", new_callable=AsyncMock, return_value=[])
    def test_list_empty(self, _m, client):
        resp = client.get("/drivers")
        assert resp.status_code == 200
        assert resp.json() == []


class TestSearchDrivers:
    @patch("src.routers.drivers.search_drivers", new_callable=AsyncMock)
    def test_search_by_name(self, mock_search, client):
        mock_search.return_value = [_driver()]
        resp = client.get("/drivers/search?name=Lewis")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    @patch("src.routers.drivers.search_drivers", new_callable=AsyncMock)
    def test_search_by_team(self, mock_search, client):
        mock_search.return_value = [_driver()]
        resp = client.get("/drivers/search?team=Ferrari")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    @patch("src.routers.drivers.search_drivers", new_callable=AsyncMock, return_value=[])
    def test_search_no_results(self, _m, client):
        resp = client.get("/drivers/search?name=Nobody")
        assert resp.status_code == 200
        assert resp.json() == []


class TestGetDriver:
    @patch("src.routers.drivers.get_driver_by_id", new_callable=AsyncMock)
    def test_found(self, mock_get, client):
        mock_get.return_value = _driver()
        resp = client.get(f"/drivers/{FAKE_DRIVER_ID}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Lewis Hamilton"

    @patch("src.routers.drivers.get_driver_by_id", new_callable=AsyncMock)
    def test_not_found(self, mock_get, client):
        from fastapi import HTTPException
        mock_get.side_effect = HTTPException(404, "Driver not found")
        resp = client.get(f"/drivers/{FAKE_DRIVER_ID}")
        assert resp.status_code == 404


# ── Admin-only endpoints ─────────────────────────────────────────────────────
class TestCreateDriver:
    @patch("src.routers.drivers.create_driver_db", new_callable=AsyncMock)
    def test_admin_can_create(self, mock_create, admin_client):
        mock_create.return_value = _driver()
        resp = admin_client.post("/drivers", json={
            "name": "Lewis Hamilton", "number": 44, "team": "Ferrari",
        })
        assert resp.status_code == 201
        assert resp.json()["name"] == "Lewis Hamilton"

    def test_regular_user_forbidden(self, auth_client):
        resp = auth_client.post("/drivers", json={
            "name": "Lewis Hamilton", "number": 44, "team": "Ferrari",
        })
        assert resp.status_code == 403

    def test_unauthenticated_rejected(self, client):
        resp = client.post("/drivers", json={
            "name": "Lewis Hamilton", "number": 44, "team": "Ferrari",
        })
        assert resp.status_code == 401


class TestUpdateDriver:
    @patch("src.routers.drivers.update_driver_db", new_callable=AsyncMock)
    def test_admin_can_update(self, mock_update, admin_client):
        mock_update.return_value = _driver(team="Mercedes")
        resp = admin_client.patch(f"/drivers/{FAKE_DRIVER_ID}", json={"team": "Mercedes"})
        assert resp.status_code == 200
        assert resp.json()["team"] == "Mercedes"

    def test_regular_user_forbidden(self, auth_client):
        resp = auth_client.patch(f"/drivers/{FAKE_DRIVER_ID}", json={"team": "Mercedes"})
        assert resp.status_code == 403


class TestDeleteDriver:
    @patch("src.routers.drivers.delete_driver_db", new_callable=AsyncMock, return_value=True)
    def test_admin_can_delete(self, _del, admin_client):
        resp = admin_client.delete(f"/drivers/{FAKE_DRIVER_ID}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_regular_user_forbidden(self, auth_client):
        resp = auth_client.delete(f"/drivers/{FAKE_DRIVER_ID}")
        assert resp.status_code == 403
