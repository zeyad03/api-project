"""Tests for /head-to-head endpoints.

Category: **api** – HTTP request → response tests via TestClient.
"""

import pytest
from unittest.mock import AsyncMock, patch

from src.core.exceptions import DriverNotFoundError
from src.models.driver import Driver
from src.models.head_to_head import HeadToHeadVote

from .conftest import (
    FAKE_DRIVER_ID, FAKE_DRIVER2_ID, FAKE_USER_ID, FAKE_VOTE_ID, TIMESTAMP,
)

pytestmark = pytest.mark.api


def _driver(did=FAKE_DRIVER_ID, name="Lewis Hamilton", **kw):
    defaults = dict(
        id=did, name=name, number=44, team="Ferrari",
        nationality="British", active=True, created_at=TIMESTAMP,
    )
    defaults.update(kw)
    return Driver(**defaults)


def _vote(**overrides):
    defaults = dict(
        id=FAKE_VOTE_ID, driver1_id=FAKE_DRIVER_ID, driver2_id=FAKE_DRIVER2_ID,
        user_id=FAKE_USER_ID, winner_id=FAKE_DRIVER_ID, created_at=TIMESTAMP,
    )
    defaults.update(overrides)
    return HeadToHeadVote(**defaults)


class TestCompare:
    @patch("src.routers.head_to_head.get_h2h_results", new_callable=AsyncMock)
    @patch("src.routers.head_to_head.get_driver_by_name", new_callable=AsyncMock)
    def test_compare_two_drivers(self, mock_driver, mock_votes, client):
        mock_driver.side_effect = [
            _driver(FAKE_DRIVER_ID, "Lewis Hamilton"),
            _driver(FAKE_DRIVER2_ID, "Max Verstappen", number=1),
        ]
        mock_votes.return_value = {
            "driver1_id": FAKE_DRIVER_ID, "driver2_id": FAKE_DRIVER2_ID,
            "driver1_votes": 5, "driver2_votes": 3, "total_votes": 8,
        }
        resp = client.get("/head-to-head/compare/Lewis%20Hamilton/Max%20Verstappen")
        assert resp.status_code == 200
        body = resp.json()
        assert body["driver1"]["name"] == "Lewis Hamilton"
        assert body["driver2"]["name"] == "Max Verstappen"
        assert body["community_votes"]["total_votes"] == 8

    @patch("src.routers.head_to_head.get_driver_by_name", new_callable=AsyncMock)
    def test_driver_not_found(self, mock_driver, client):
        mock_driver.side_effect = DriverNotFoundError(FAKE_DRIVER_ID)
        resp = client.get("/head-to-head/compare/Lewis%20Hamilton/Max%20Verstappen")
        assert resp.status_code == 404


class TestVote:
    @patch("src.routers.head_to_head.cast_h2h_vote", new_callable=AsyncMock)
    def test_cast_vote(self, mock_vote, auth_client):
        mock_vote.return_value = _vote()
        resp = auth_client.post("/head-to-head/vote", json={
            "driver1_id": FAKE_DRIVER_ID,
            "driver2_id": FAKE_DRIVER2_ID,
            "winner_id": FAKE_DRIVER_ID,
        })
        assert resp.status_code == 201
        assert resp.json()["winner_id"] == FAKE_DRIVER_ID

    @patch("src.routers.head_to_head.cast_h2h_vote", new_callable=AsyncMock)
    @patch("src.routers.head_to_head.get_driver_by_name", new_callable=AsyncMock)
    def test_cast_vote_by_name(self, mock_name, mock_vote, auth_client):
        mock_name.return_value = _driver(FAKE_DRIVER_ID, "Lewis Hamilton")
        mock_vote.return_value = _vote()
        resp = auth_client.post("/head-to-head/vote", json={
            "driver1_name": "Lewis Hamilton",
            "driver2_id": FAKE_DRIVER2_ID,
            "winner_name": "Lewis Hamilton",
        })
        assert resp.status_code == 201

    def test_cast_vote_missing_id_and_name(self, auth_client):
        resp = auth_client.post("/head-to-head/vote", json={
            "driver1_id": FAKE_DRIVER_ID,
            "driver2_id": FAKE_DRIVER2_ID,
        })
        assert resp.status_code == 400

    def test_unauthenticated(self, client):
        resp = client.post("/head-to-head/vote", json={
            "driver1_id": FAKE_DRIVER_ID,
            "driver2_id": FAKE_DRIVER2_ID,
            "winner_id": FAKE_DRIVER_ID,
        })
        assert resp.status_code == 401
