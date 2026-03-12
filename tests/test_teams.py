"""Tests for /teams endpoints.

Category: **api** – HTTP request → response tests via TestClient.
"""

import pytest
from unittest.mock import AsyncMock, patch

from src.core.exceptions import TeamNotFoundError
from src.models.team import Team

from .conftest import FAKE_TEAM_ID, TIMESTAMP

pytestmark = pytest.mark.api


def _team(**overrides):
    defaults = dict(
        id=FAKE_TEAM_ID, name="Ferrari", full_name="Scuderia Ferrari",
        base="Maranello, Italy", team_principal="Frédéric Vasseur",
        championships=16, first_entry=1950, car="SF-25", engine="Ferrari",
        active=True, created_at=TIMESTAMP,
    )
    defaults.update(overrides)
    return Team(**defaults)


# ── Public endpoints ─────────────────────────────────────────────────────────
class TestListTeams:
    @patch("src.routers.teams.get_all_teams", new_callable=AsyncMock)
    def test_list_all(self, mock_get, client):
        mock_get.return_value = ([_team()], 1)
        resp = client.get("/teams")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 1
        assert resp.json()["data"][0]["name"] == "Ferrari"
        assert resp.json()["total"] == 1

    @patch("src.routers.teams.get_all_teams", new_callable=AsyncMock)
    def test_list_active_only(self, mock_get, client):
        mock_get.return_value = ([_team()], 1)
        resp = client.get("/teams?active_only=true")
        assert resp.status_code == 200

    @patch("src.routers.teams.get_all_teams", new_callable=AsyncMock, return_value=([], 0))
    def test_list_empty(self, _m, client):
        resp = client.get("/teams")
        assert resp.status_code == 200
        assert resp.json()["data"] == []


class TestSearchTeams:
    @patch("src.routers.teams.search_teams", new_callable=AsyncMock)
    def test_search_by_name(self, mock_search, client):
        mock_search.return_value = ([_team()], 1)
        resp = client.get("/teams/search?name=Ferrari")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 1

    @patch("src.routers.teams.search_teams", new_callable=AsyncMock, return_value=([], 0))
    def test_search_no_results(self, _m, client):
        resp = client.get("/teams/search?name=Nobody")
        assert resp.status_code == 200
        assert resp.json() == []


class TestGetTeam:
    @patch("src.routers.teams.get_team_by_id", new_callable=AsyncMock)
    def test_found(self, mock_get, client):
        mock_get.return_value = _team()
        resp = client.get(f"/teams/{FAKE_TEAM_ID}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Ferrari"

    @patch("src.routers.teams.get_team_by_id", new_callable=AsyncMock)
    def test_not_found(self, mock_get, client):
        mock_get.side_effect = TeamNotFoundError(FAKE_TEAM_ID)
        resp = client.get(f"/teams/{FAKE_TEAM_ID}")
        assert resp.status_code == 404


# ── Admin-only endpoints ─────────────────────────────────────────────────────
class TestCreateTeam:
    @patch("src.routers.teams.create_team_db", new_callable=AsyncMock)
    def test_admin_can_create(self, mock_create, admin_client):
        mock_create.return_value = _team()
        resp = admin_client.post("/teams", json={"name": "Ferrari"})
        assert resp.status_code == 201
        assert resp.json()["name"] == "Ferrari"

    def test_regular_user_forbidden(self, auth_client):
        resp = auth_client.post("/teams", json={"name": "Ferrari"})
        assert resp.status_code == 403

    def test_unauthenticated_rejected(self, client):
        resp = client.post("/teams", json={"name": "Ferrari"})
        assert resp.status_code == 401


class TestUpdateTeam:
    @patch("src.routers.teams.update_team_db", new_callable=AsyncMock)
    def test_admin_can_update(self, mock_update, admin_client):
        mock_update.return_value = _team(team_principal="New Boss")
        resp = admin_client.patch(f"/teams/{FAKE_TEAM_ID}", json={"team_principal": "New Boss"})
        assert resp.status_code == 200

    def test_regular_user_forbidden(self, auth_client):
        resp = auth_client.patch(f"/teams/{FAKE_TEAM_ID}", json={"name": "X"})
        assert resp.status_code == 403


class TestDeleteTeam:
    @patch("src.routers.teams.delete_team_db", new_callable=AsyncMock, return_value=True)
    def test_admin_can_delete(self, _del, admin_client):
        resp = admin_client.delete(f"/teams/{FAKE_TEAM_ID}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_regular_user_forbidden(self, auth_client):
        resp = auth_client.delete(f"/teams/{FAKE_TEAM_ID}")
        assert resp.status_code == 403
