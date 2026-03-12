"""Tests for native MCP endpoint (/mcp).

Category: **api** – HTTP request → response tests via TestClient.
"""

import pytest
from unittest.mock import AsyncMock, patch

from src.core.security import create_access_token
from src.models.driver import Driver

from .conftest import FAKE_DRIVER_ID, TIMESTAMP

pytestmark = pytest.mark.api


def _driver() -> Driver:
    return Driver(
        id=FAKE_DRIVER_ID,
        name="Lewis Hamilton",
        number=44,
        team="Ferrari",
        nationality="British",
        date_of_birth="1985-01-07",
        championships=7,
        wins=103,
        podiums=197,
        poles=104,
        bio="",
        active=True,
        created_at=TIMESTAMP,
    )


def _mcp_call(tool_name: str, arguments: dict | None = None, req_id: int = 1) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments or {},
        },
    }


# ── Protocol-level tests ────────────────────────────────────────────────────
class TestMCPProtocol:
    def test_initialize(self, client):
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {},
        }
        resp = client.post("/mcp", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        assert body["jsonrpc"] == "2.0"
        assert body["id"] == 1
        assert body["result"]["serverInfo"]["name"] == "f1-facts-mcp"

    def test_tools_list_contains_all_tools(self, client):
        payload = {
            "jsonrpc": "2.0",
            "id": "abc",
            "method": "tools/list",
            "params": {},
        }
        resp = client.post("/mcp", json=payload)
        assert resp.status_code == 200
        tools = resp.json()["result"]["tools"]
        names = {t["name"] for t in tools}
        expected = {
            "list_drivers", "search_drivers", "get_driver_season_stats",
            "list_teams", "search_teams",
            "list_circuits", "search_circuits",
            "list_seasons", "list_races", "list_race_results",
            "get_random_fact", "list_facts",
            "get_prediction_leaderboard",
        }
        assert expected == names

    def test_unknown_method(self, client):
        payload = {"jsonrpc": "2.0", "id": 99, "method": "foo/bar", "params": {}}
        resp = client.post("/mcp", json=payload)
        assert resp.json()["error"]["code"] == -32601

    def test_unknown_tool(self, client):
        resp = client.post("/mcp", json=_mcp_call("nonexistent_tool"))
        assert resp.json()["error"]["code"] == -32601

    def test_invalid_jsonrpc_version(self, client):
        payload = {"jsonrpc": "1.0", "id": 1, "method": "initialize", "params": {}}
        resp = client.post("/mcp", json=payload)
        assert resp.json()["error"]["code"] == -32600

    def test_discovery_endpoint(self, client):
        resp = client.get("/mcp")
        assert resp.status_code == 200
        body = resp.json()
        assert body["endpoint"] == "/mcp"
        assert "tools_require_auth" in body


# ── Tool call tests ──────────────────────────────────────────────────────────
class TestMCPTools:
    @patch("src.mcp.tools.get_all_drivers", new_callable=AsyncMock)
    def test_list_drivers(self, mock_fn, client):
        mock_fn.return_value = ([_driver()], 1)
        resp = client.post("/mcp", json=_mcp_call("list_drivers", {"active_only": True, "limit": 10}))
        body = resp.json()
        assert body["result"]["isError"] is False
        assert body["result"]["structuredContent"][0]["name"] == "Lewis Hamilton"
        assert mock_fn.call_args.kwargs["active_only"] is True

    @patch("src.mcp.tools.search_drivers", new_callable=AsyncMock)
    def test_search_drivers(self, mock_fn, client):
        mock_fn.return_value = ([_driver()], 1)
        resp = client.post("/mcp", json=_mcp_call("search_drivers", {"name": "Lewis"}))
        assert resp.json()["result"]["isError"] is False
        mock_fn.assert_awaited_once()

    @patch("src.mcp.tools.get_driver_season_stats", new_callable=AsyncMock)
    def test_driver_season_stats(self, mock_fn, client):
        mock_fn.return_value = []
        resp = client.post("/mcp", json=_mcp_call("get_driver_season_stats", {"season_year": 2024}))
        assert resp.json()["result"]["isError"] is False
        mock_fn.assert_awaited_once()

    @patch("src.mcp.tools.get_all_teams", new_callable=AsyncMock)
    def test_list_teams(self, mock_fn, client):
        mock_fn.return_value = ([], 0)
        resp = client.post("/mcp", json=_mcp_call("list_teams"))
        assert resp.json()["result"]["isError"] is False

    @patch("src.mcp.tools.search_teams", new_callable=AsyncMock)
    def test_search_teams(self, mock_fn, client):
        mock_fn.return_value = ([], 0)
        resp = client.post("/mcp", json=_mcp_call("search_teams", {"name": "Ferrari"}))
        assert resp.json()["result"]["isError"] is False

    @patch("src.mcp.tools.get_all_circuits", new_callable=AsyncMock)
    def test_list_circuits(self, mock_fn, client):
        mock_fn.return_value = ([], 0)
        resp = client.post("/mcp", json=_mcp_call("list_circuits", {"active_only": True}))
        assert resp.json()["result"]["isError"] is False
        assert mock_fn.call_args.kwargs["active_only"] is True

    @patch("src.mcp.tools.search_circuits", new_callable=AsyncMock)
    def test_search_circuits(self, mock_fn, client):
        mock_fn.return_value = ([], 0)
        resp = client.post("/mcp", json=_mcp_call("search_circuits", {"country": "Italy"}))
        assert resp.json()["result"]["isError"] is False

    @patch("src.mcp.tools.get_all_seasons", new_callable=AsyncMock)
    def test_list_seasons(self, mock_fn, client):
        mock_fn.return_value = ([], 0)
        resp = client.post("/mcp", json=_mcp_call("list_seasons"))
        assert resp.json()["result"]["isError"] is False

    @patch("src.mcp.tools.get_seasons_range", new_callable=AsyncMock)
    def test_list_seasons_with_range(self, mock_fn, client):
        mock_fn.return_value = []
        resp = client.post("/mcp", json=_mcp_call("list_seasons", {"start_year": 2020, "end_year": 2024}))
        assert resp.json()["result"]["isError"] is False
        mock_fn.assert_awaited_once()

    @patch("src.mcp.tools.get_all_races", new_callable=AsyncMock)
    def test_list_races(self, mock_fn, client):
        mock_fn.return_value = ([], 0)
        resp = client.post("/mcp", json=_mcp_call("list_races", {"season_year": 2024}))
        assert resp.json()["result"]["isError"] is False

    @patch("src.mcp.tools.get_race_results", new_callable=AsyncMock)
    def test_list_race_results(self, mock_fn, client):
        mock_fn.return_value = []
        resp = client.post("/mcp", json=_mcp_call("list_race_results", {"season_year": 2024}))
        assert resp.json()["result"]["isError"] is False

    @patch("src.mcp.tools.get_random_fact", new_callable=AsyncMock)
    def test_get_random_fact(self, mock_fn, client):
        mock_fn.return_value = None
        resp = client.post("/mcp", json=_mcp_call("get_random_fact"))
        result = resp.json()["result"]
        assert result["isError"] is False
        assert "No facts available" in result["structuredContent"]["message"]

    @patch("src.mcp.tools.get_all_facts", new_callable=AsyncMock)
    def test_list_facts(self, mock_fn, client):
        mock_fn.return_value = []
        resp = client.post("/mcp", json=_mcp_call("list_facts", {"category": "history"}))
        assert resp.json()["result"]["isError"] is False

    @patch("src.mcp.tools.get_prediction_leaderboard", new_callable=AsyncMock)
    def test_prediction_leaderboard(self, mock_fn, client):
        mock_fn.return_value = []
        resp = client.post(
            "/mcp",
            json=_mcp_call("get_prediction_leaderboard", {"category": "driver_championship"}),
        )
        assert resp.json()["result"]["isError"] is False

    def test_prediction_leaderboard_invalid_category(self, client):
        resp = client.post(
            "/mcp",
            json=_mcp_call("get_prediction_leaderboard", {"category": "invalid"}),
        )
        assert resp.json()["error"]["code"] == -32602


# ── Error propagation tests ─────────────────────────────────────────────────
class TestMCPErrorPropagation:
    @patch("src.mcp.tools.get_all_drivers", new_callable=AsyncMock)
    def test_api_error_surfaces_detail(self, mock_fn, client):
        """F1FactsAPIError exceptions should surface as MCP tool errors with detail."""
        from src.core.exceptions import DriverNotFoundError
        mock_fn.side_effect = DriverNotFoundError("abc123")
        resp = client.post("/mcp", json=_mcp_call("list_drivers"))
        result = resp.json()["result"]
        assert result["isError"] is True
        assert "not found" in result["content"][0]["text"].lower()


# ── Auth tests ───────────────────────────────────────────────────────────────
class TestMCPAuth:
    @patch("src.mcp.tools.get_all_drivers", new_callable=AsyncMock)
    def test_requires_auth_when_enabled(self, mock_fn, client):
        mock_fn.return_value = [_driver()]
        with patch("src.mcp.auth.settings.MCP_REQUIRE_AUTH", True):
            resp = client.post("/mcp", json=_mcp_call("list_drivers"))
        assert resp.json()["error"]["code"] == -32001

    @patch("src.mcp.tools.get_all_drivers", new_callable=AsyncMock)
    def test_rejects_invalid_token(self, mock_fn, client):
        mock_fn.return_value = [_driver()]
        with patch("src.mcp.auth.settings.MCP_REQUIRE_AUTH", True):
            resp = client.post(
                "/mcp", json=_mcp_call("list_drivers"),
                headers={"Authorization": "Bearer not-a-real-jwt"},
            )
        assert resp.json()["error"]["code"] == -32001

    @patch("src.mcp.tools.get_all_drivers", new_callable=AsyncMock)
    def test_accepts_valid_token(self, mock_fn, client):
        mock_fn.return_value = [_driver()]
        token = create_access_token(
            {"sub": "mcp-user", "user_id": "507f1f77bcf86cd799439099", "role": "user", "is_admin": False}
        )
        with patch("src.mcp.auth.settings.MCP_REQUIRE_AUTH", True):
            resp = client.post(
                "/mcp", json=_mcp_call("list_drivers"),
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.json()["result"]["structuredContent"][0]["name"] == "Lewis Hamilton"
