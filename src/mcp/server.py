"""MCP JSON-RPC 2.0 server — protocol handling and FastAPI routes.

This module owns the ``APIRouter``, request validation, and dispatch.
Tool definitions and handlers live in ``src.mcp.tools``.
Auth helpers live in ``src.mcp.auth``.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from src.config.settings import settings
from src.core.exceptions import F1FactsAPIError
from src.mcp.auth import authenticate_tool_call
from src.mcp.tools import TOOLS, get_tool_definitions, mcp_error_result

router = APIRouter()
log = logging.getLogger("f1api.mcp")

# ── Constants ────────────────────────────────────────────────────────────────
JSONRPC_VERSION = "2.0"
MCP_PROTOCOL_VERSION = "2025-03-26"
INVALID_REQUEST = "Invalid Request"


# ── Pydantic model for Swagger UI ───────────────────────────────────────────
class MCPRequest(BaseModel):
    """JSON-RPC 2.0 request envelope used by MCP."""

    jsonrpc: str = Field(
        default=JSONRPC_VERSION,
        description="Must be '2.0'.",
        examples=["2.0"],
    )
    id: int | str | None = Field(
        default=None,
        description="Request identifier.",
        examples=[1],
    )
    method: str = Field(
        description="MCP method: initialize, tools/list, or tools/call.",
        examples=["initialize"],
    )
    params: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Method parameters. For tools/call send "
            '{"name": "<tool>", "arguments": {...}}.'
        ),
        examples=[{}],
    )


# ── JSON-RPC helpers ─────────────────────────────────────────────────────────
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


def _validate_jsonrpc_payload(payload: dict) -> tuple[str, Any, dict[str, Any]] | None:
    """Validate base JSON-RPC fields.

    Returns ``(method, request_id, params)`` when valid, else ``None``.
    """
    if payload.get("jsonrpc") != JSONRPC_VERSION:
        return None

    method = payload.get("method")
    request_id = payload.get("id")
    params = payload.get("params") or {}

    if not isinstance(method, str):
        return None
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


# ── Tool call dispatch ───────────────────────────────────────────────────────
async def _handle_tool_call(
    request: Request, request_id: Any, params: dict[str, Any]
) -> dict[str, Any]:
    is_authenticated, error_message, _ = await authenticate_tool_call(request)
    if not is_authenticated:
        log.warning("MCP auth rejected: %s", error_message)
        return _error_response(-32001, error_message, request_id)

    tool_name = params.get("name")
    arguments = params.get("arguments", {})

    if not isinstance(tool_name, str):
        return _error_response(-32602, "Invalid params: tool name is required", request_id)
    if not isinstance(arguments, dict):
        return _error_response(-32602, "Invalid params: arguments must be an object", request_id)

    tool = TOOLS.get(tool_name)
    if tool is None:
        log.warning("MCP unknown tool requested: %s", tool_name)
        return _error_response(-32601, f"Unknown tool: {tool_name}", request_id)

    try:
        log.info("MCP tool call: %s", tool_name)
        result = await tool(request, arguments)
        return _success_response(result, request_id)
    except ValueError as exc:
        return _error_response(-32602, f"Invalid params: {exc}", request_id)
    except F1FactsAPIError as exc:
        # Surface the same error detail the REST API would return
        return _success_response(
            mcp_error_result(exc.detail), request_id,
        )
    except Exception:
        log.exception("MCP tool '%s' execution failed", tool_name)
        return _error_response(-32603, "Tool execution failed", request_id)


# ── Routes ───────────────────────────────────────────────────────────────────
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
async def mcp_rpc(body: MCPRequest, request: Request) -> dict[str, Any]:
    """Handle MCP JSON-RPC messages.

    Supported methods:
    - **initialize** — handshake, returns server info & capabilities
    - **tools/list** — discover available tools
    - **tools/call** — execute a tool
    """
    payload = body.model_dump()

    validated = _validate_jsonrpc_payload(payload)
    if validated is None:
        return _error_response(-32600, INVALID_REQUEST, body.id)
    method, request_id, params = validated

    if method == "initialize":
        return _success_response(_initialize_result(), request_id)

    if method == "tools/list":
        return _success_response({"tools": get_tool_definitions()}, request_id)

    if method == "tools/call":
        return await _handle_tool_call(request, request_id, params)

    return _error_response(-32601, f"Method not found: {method}", request_id)
