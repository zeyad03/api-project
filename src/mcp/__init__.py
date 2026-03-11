"""MCP (Model Context Protocol) package.

Exposes a single ``router`` that the main application mounts at ``/mcp``.
"""

from src.mcp.server import router

__all__ = ["router"]
