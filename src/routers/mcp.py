"""Native MCP (Model Context Protocol) router.

Implements a minimal JSON-RPC 2.0 MCP surface so MCP clients can discover
and call read-only tools directly against this API.
"""

from __future__ import annotations

import json
from typing import Any, Awaitable, Callable

from fastapi import APIRouter, Request
from fastapi.encoders import jsonable_encoder

from src.config.settings import settings
from src.db.drivers import get_all_drivers, search_drivers
from src.db.races import get_all_races
from src.db.teams import get_all_teams
from src.models.user import TokenData
from src.core.security import decode_token

router = APIRouter()

JSONRPC_VERSION = "2.0"
MCP_PROTOCOL_VERSION = "2025-03-26"
INVALID_REQUEST = "Invalid Request"
AUTH_REQUIRED_MESSAGE = "Authentication required for MCP tools"
INVALID_AUTH_HEADER_MESSAGE = "Invalid Authorization header. Use: Bearer <token>"
INVALID_TOKEN_MESSAGE = "Invalid authentication token"

ToolHandler = Callable[[Request, dict[str, Any]], Awaitable[dict[str, Any]]]


def _success_response(result: dict[str, Any], request_id: Any) -> dict[str, Any]:
    return {
        "jsonrpc": JSONRPC_VERSION,
        "id": request_id,
        "result": result,
    }


def _error_response(code: int, message: str, request_id: Any = None) -> dict[str, Any]:
    return {
        "jsonrpc": JSONRPC_VERSION,
        "id": request_id,
        "error": {
            "code": code,
            "message": message,
        },
    }


def _mcp_text_result(data: Any) -> dict[str, Any]:
    encoded = jsonable_encoder(data)
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(encoded, ensure_ascii=False),
            }
        ],
        "structuredContent": encoded,
        "isError": False,
    }


def _validate_jsonrpc_payload(payload: Any) -> tuple[str, Any, dict[str, Any]] | None:
    """Validate base JSON-RPC fields.

    Returns a tuple of (method, request_id, params) when valid.
    Returns None when payload is invalid.
    """
    if not isinstance(payload, dict):
        return None

    if payload.get("jsonrpc") != JSONRPC_VERSION:
        return None

    method = payload.get("method")
    request_id = payload.get("id")
    params = payload.get("params", {})

    if not isinstance(method, str):
        return None
    if params is None:
        params = {}
    if not isinstance(params, dict):
        return None

    return method, request_id, params


def _initialize_result() -> dict[str, Any]:
    return {
        "protocolVersion": MCP_PROTOCOL_VERSION,
        "serverInfo": {
            "name": "f1-facts-mcp",
            "version": "1.0.0",
        },
        "capabilities": {
            "tools": {
                "listChanged": False,
            }
        },
    }


def _extract_bearer_token(request: Request) -> str | None:
    auth_header = request.headers.get("authorization", "")
    if not auth_header:
        return None
    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return ""
    return token.strip()


def _authenticate_tool_call(request: Request) -> tuple[bool, str, TokenData | None]:
    if not settings.MCP_REQUIRE_AUTH:
        return True, "", None

    token = _extract_bearer_token(request)
    if token is None:
        return False, AUTH_REQUIRED_MESSAGE, None
    if token == "":
        return False, INVALID_AUTH_HEADER_MESSAGE, None

    try:
        user = decode_token(token)
    except Exception:
        return False, INVALID_TOKEN_MESSAGE, None

    return True, "", user


async def _handle_tool_call(
    request: Request, request_id: Any, params: dict[str, Any]
) -> dict[str, Any]:
    is_authenticated, error_message, _ = _authenticate_tool_call(request)
    if not is_authenticated:
        return _error_response(-32001, error_message, request_id)

    tool_name = params.get("name")
    arguments = params.get("arguments", {})

    if not isinstance(tool_name, str):
        return _error_response(-32602, "Invalid params: tool name is required", request_id)
    if not isinstance(arguments, dict):
        return _error_response(-32602, "Invalid params: arguments must be an object", request_id)

    tool = TOOLS.get(tool_name)
    if tool is None:
        return _error_response(-32601, f"Unknown tool: {tool_name}", request_id)

    try:
        result = await tool(request, arguments)
        return _success_response(result, request_id)
    except ValueError as exc:
        return _error_response(-32602, f"Invalid params: {exc}", request_id)
    except Exception:
        return _error_response(-32603, "Tool execution failed", request_id)


def _tool_definitions() -> list[dict[str, Any]]:
    return [
        {
            "name": "list_drivers",
            "description": "List F1 drivers with optional active filter.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "active_only": {"type": "boolean", "default": False},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "search_drivers",
            "description": "Search drivers by name and/or team.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "team": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "list_teams",
            "description": "List F1 teams with optional active filter.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "active_only": {"type": "boolean", "default": False},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "list_races",
            "description": "List races filtered by season year and/or circuit id.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "season_year": {"type": "integer"},
                    "circuit_id": {"type": "integer"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
                },
                "additionalProperties": False,
            },
        },
    ]


def _get_limit(args: dict[str, Any]) -> int:
    limit = args.get("limit", 20)
    if not isinstance(limit, int):
        raise ValueError("'limit' must be an integer")
    if limit < 1 or limit > 100:
        raise ValueError("'limit' must be between 1 and 100")
    return limit


async def _tool_list_drivers(request: Request, args: dict[str, Any]) -> dict[str, Any]:
    active_only = bool(args.get("active_only", False))
    limit = _get_limit(args)
    rows = await get_all_drivers(request.app.state.db, active_only=active_only)
    return _mcp_text_result(rows[:limit])


async def _tool_search_drivers(request: Request, args: dict[str, Any]) -> dict[str, Any]:
    name = args.get("name")
    team = args.get("team")
    if name is not None and not isinstance(name, str):
        raise ValueError("'name' must be a string")
    if team is not None and not isinstance(team, str):
        raise ValueError("'team' must be a string")
    limit = _get_limit(args)
    rows = await search_drivers(request.app.state.db, name=name, team=team)
    return _mcp_text_result(rows[:limit])


async def _tool_list_teams(request: Request, args: dict[str, Any]) -> dict[str, Any]:
    active_only = bool(args.get("active_only", False))
    limit = _get_limit(args)
    rows = await get_all_teams(request.app.state.db, active_only=active_only)
    return _mcp_text_result(rows[:limit])


async def _tool_list_races(request: Request, args: dict[str, Any]) -> dict[str, Any]:
    season_year = args.get("season_year")
    circuit_id = args.get("circuit_id")
    if season_year is not None and not isinstance(season_year, int):
        raise ValueError("'season_year' must be an integer")
    if circuit_id is not None and not isinstance(circuit_id, int):
        raise ValueError("'circuit_id' must be an integer")
    limit = _get_limit(args)
    rows = await get_all_races(
        request.app.state.db,
        season_year=season_year,
        circuit_id=circuit_id,
    )
    return _mcp_text_result(rows[:limit])


TOOLS: dict[str, ToolHandler] = {
    "list_drivers": _tool_list_drivers,
    "search_drivers": _tool_search_drivers,
    "list_teams": _tool_list_teams,
    "list_races": _tool_list_races,
}


@router.get("")
async def mcp_discovery() -> dict[str, Any]:
    """Basic discovery endpoint for humans and health checks."""
    return {
        "name": "F1 Facts MCP",
        "protocol": "MCP over JSON-RPC",
        "endpoint": "/mcp",
        "methods": ["initialize", "tools/list", "tools/call"],
        "tools_require_auth": settings.MCP_REQUIRE_AUTH,
    }


@router.post("")
async def mcp_rpc(request: Request) -> dict[str, Any]:
    """Handle MCP JSON-RPC messages.

    Supported methods:
    - initialize
    - tools/list
    - tools/call
    """
    try:
        payload = await request.json()
    except Exception:
        return _error_response(-32700, "Parse error")

    if not isinstance(payload, dict):
        return _error_response(-32600, INVALID_REQUEST)

    validated = _validate_jsonrpc_payload(payload)
    if validated is None:
        return _error_response(-32600, INVALID_REQUEST, payload.get("id"))
    method, request_id, params = validated

    if method == "initialize":
        return _success_response(_initialize_result(), request_id)

    if method == "tools/list":
        return _success_response({"tools": _tool_definitions()}, request_id)

    if method == "tools/call":
        return await _handle_tool_call(request, request_id, params)

    return _error_response(-32601, f"Method not found: {method}", request_id)
