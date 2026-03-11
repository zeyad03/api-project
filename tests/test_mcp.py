"""Tests for native MCP endpoint (/mcp)."""

from unittest.mock import AsyncMock, patch

from src.core.security import create_access_token
from src.models.driver import Driver

from .conftest import FAKE_DRIVER_ID, TIMESTAMP


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


class TestMCP:
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

    def test_tools_list(self, client):
        payload = {
            "jsonrpc": "2.0",
            "id": "abc",
            "method": "tools/list",
            "params": {},
        }
        resp = client.post("/mcp", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        tools = body["result"]["tools"]
        names = {tool["name"] for tool in tools}
        assert "list_drivers" in names
        assert "list_teams" in names
        assert "list_races" in names

    @patch("src.routers.mcp.get_all_drivers", new_callable=AsyncMock)
    def test_tools_call_list_drivers(self, mock_get_all_drivers, client):
        mock_get_all_drivers.return_value = [_driver()]

        payload = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "list_drivers",
                "arguments": {"active_only": True, "limit": 10},
            },
        }
        resp = client.post("/mcp", json=payload)
        assert resp.status_code == 200
        body = resp.json()

        assert body["result"]["isError"] is False
        assert body["result"]["structuredContent"][0]["name"] == "Lewis Hamilton"
        mock_get_all_drivers.assert_awaited_once()
        kwargs = mock_get_all_drivers.call_args.kwargs
        assert kwargs["active_only"] is True

    @patch("src.routers.mcp.get_all_drivers", new_callable=AsyncMock)
    def test_tools_call_requires_auth_when_enabled(self, mock_get_all_drivers, client):
        mock_get_all_drivers.return_value = [_driver()]
        payload = {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {
                "name": "list_drivers",
                "arguments": {},
            },
        }

        with patch("src.routers.mcp.settings.MCP_REQUIRE_AUTH", True):
            resp = client.post("/mcp", json=payload)

        assert resp.status_code == 200
        body = resp.json()
        assert body["error"]["code"] == -32001
        assert "Authentication required" in body["error"]["message"]

    @patch("src.routers.mcp.get_all_drivers", new_callable=AsyncMock)
    def test_tools_call_rejects_invalid_token_when_enabled(self, mock_get_all_drivers, client):
        mock_get_all_drivers.return_value = [_driver()]
        payload = {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {
                "name": "list_drivers",
                "arguments": {},
            },
        }

        with patch("src.routers.mcp.settings.MCP_REQUIRE_AUTH", True):
            resp = client.post(
                "/mcp",
                json=payload,
                headers={"Authorization": "Bearer not-a-real-jwt"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["error"]["code"] == -32001
        assert "Invalid authentication token" in body["error"]["message"]

    @patch("src.routers.mcp.get_all_drivers", new_callable=AsyncMock)
    def test_tools_call_accepts_valid_token_when_enabled(self, mock_get_all_drivers, client):
        mock_get_all_drivers.return_value = [_driver()]
        token = create_access_token(
            {
                "sub": "mcp-user",
                "user_id": "507f1f77bcf86cd799439099",
                "is_admin": False,
            }
        )
        payload = {
            "jsonrpc": "2.0",
            "id": 8,
            "method": "tools/call",
            "params": {
                "name": "list_drivers",
                "arguments": {"limit": 5},
            },
        }

        with patch("src.routers.mcp.settings.MCP_REQUIRE_AUTH", True):
            resp = client.post(
                "/mcp",
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert "result" in body
        assert body["result"]["structuredContent"][0]["name"] == "Lewis Hamilton"
        mock_get_all_drivers.assert_awaited_once()

    def test_unknown_method(self, client):
        payload = {
            "jsonrpc": "2.0",
            "id": 99,
            "method": "foo/bar",
            "params": {},
        }
        resp = client.post("/mcp", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        assert body["error"]["code"] == -32601
