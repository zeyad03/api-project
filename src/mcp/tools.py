"""MCP tool definitions, handlers and registry.

Every handler mirrors a public REST endpoint by calling the exact same
``src.db`` query function that the corresponding router uses.
"""

from __future__ import annotations

import json
from typing import Any, Awaitable, Callable

from fastapi import Request
from fastapi.encoders import jsonable_encoder

from src.db.circuits import get_all_circuits, search_circuits
from src.db.drivers import get_all_drivers, get_driver_season_stats, search_drivers
from src.db.facts import get_all_facts, get_random_fact
from src.db.predictions import get_prediction_leaderboard
from src.db.races import get_all_races
from src.db.results import get_race_results
from src.db.seasons import get_all_seasons, get_seasons_range
from src.db.teams import get_all_teams, search_teams

ToolHandler = Callable[[Request, dict[str, Any]], Awaitable[dict[str, Any]]]

# ── Description constants ────────────────────────────────────────────────────
_DESC_PARTIAL_NAME = "Partial name match."
_DESC_PARTIAL_COUNTRY = "Partial country match."

LIMIT_SCHEMA: dict[str, Any] = {
    "type": "integer",
    "minimum": 1,
    "maximum": 100,
    "default": 20,
    "description": "Maximum number of results to return.",
}


# ── Result helpers ───────────────────────────────────────────────────────────
def mcp_text_result(data: Any) -> dict[str, Any]:
    """Wrap *data* in MCP ``content`` + ``structuredContent`` envelope."""
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


def mcp_error_result(message: str) -> dict[str, Any]:
    """Return an MCP-level tool error (``isError=True``)."""
    return {
        "content": [{"type": "text", "text": message}],
        "isError": True,
    }


# ── Shared argument validators ───────────────────────────────────────────────
def _get_limit(args: dict[str, Any]) -> int:
    limit = args.get("limit", 20)
    if not isinstance(limit, int):
        raise ValueError("'limit' must be an integer")
    if limit < 1 or limit > 100:
        raise ValueError("'limit' must be between 1 and 100")
    return limit


def _get_optional_int(args: dict[str, Any], key: str) -> int | None:
    val = args.get(key)
    if val is not None and not isinstance(val, int):
        raise ValueError(f"'{key}' must be an integer")
    return val


def _get_optional_str(args: dict[str, Any], key: str) -> str | None:
    val = args.get(key)
    if val is not None and not isinstance(val, str):
        raise ValueError(f"'{key}' must be a string")
    return val


# ── Tool handlers ────────────────────────────────────────────────────────────

async def _tool_list_drivers(request: Request, args: dict[str, Any]) -> dict[str, Any]:
    active_only = bool(args.get("active_only", False))
    limit = _get_limit(args)
    rows = await get_all_drivers(request.app.state.db, active_only=active_only)
    return mcp_text_result(rows[:limit])


async def _tool_search_drivers(request: Request, args: dict[str, Any]) -> dict[str, Any]:
    limit = _get_limit(args)
    rows = await search_drivers(
        request.app.state.db,
        name=_get_optional_str(args, "name"),
        team=_get_optional_str(args, "team"),
    )
    return mcp_text_result(rows[:limit])


async def _tool_get_driver_season_stats(request: Request, args: dict[str, Any]) -> dict[str, Any]:
    limit = _get_limit(args)
    rows = await get_driver_season_stats(
        request.app.state.db,
        driver_id=_get_optional_int(args, "driver_id"),
        season_year=_get_optional_int(args, "season_year"),
    )
    return mcp_text_result(rows[:limit])


async def _tool_list_teams(request: Request, args: dict[str, Any]) -> dict[str, Any]:
    active_only = bool(args.get("active_only", False))
    limit = _get_limit(args)
    rows = await get_all_teams(request.app.state.db, active_only=active_only)
    return mcp_text_result(rows[:limit])


async def _tool_search_teams(request: Request, args: dict[str, Any]) -> dict[str, Any]:
    limit = _get_limit(args)
    rows = await search_teams(
        request.app.state.db,
        name=_get_optional_str(args, "name"),
    )
    return mcp_text_result(rows[:limit])


async def _tool_list_circuits(request: Request, args: dict[str, Any]) -> dict[str, Any]:
    active_only = bool(args.get("active_only", False))
    limit = _get_limit(args)
    rows = await get_all_circuits(
        request.app.state.db,
        active_only=active_only,
        country=_get_optional_str(args, "country"),
    )
    return mcp_text_result(rows[:limit])


async def _tool_search_circuits(request: Request, args: dict[str, Any]) -> dict[str, Any]:
    limit = _get_limit(args)
    rows = await search_circuits(
        request.app.state.db,
        name=_get_optional_str(args, "name"),
        country=_get_optional_str(args, "country"),
    )
    return mcp_text_result(rows[:limit])


async def _tool_list_seasons(request: Request, args: dict[str, Any]) -> dict[str, Any]:
    limit = _get_limit(args)
    start_year = _get_optional_int(args, "start_year")
    end_year = _get_optional_int(args, "end_year")
    if start_year is not None or end_year is not None:
        rows = await get_seasons_range(
            request.app.state.db, start_year=start_year, end_year=end_year,
        )
    else:
        rows = await get_all_seasons(request.app.state.db)
    return mcp_text_result(rows[:limit])


async def _tool_list_races(request: Request, args: dict[str, Any]) -> dict[str, Any]:
    limit = _get_limit(args)
    rows = await get_all_races(
        request.app.state.db,
        season_year=_get_optional_int(args, "season_year"),
        circuit_id=_get_optional_int(args, "circuit_id"),
    )
    return mcp_text_result(rows[:limit])


async def _tool_list_race_results(request: Request, args: dict[str, Any]) -> dict[str, Any]:
    limit = _get_limit(args)
    rows = await get_race_results(
        request.app.state.db,
        race_id=_get_optional_int(args, "race_id"),
        season_year=_get_optional_int(args, "season_year"),
        driver_id=_get_optional_int(args, "driver_id"),
        constructor_id=_get_optional_int(args, "constructor_id"),
        limit=limit,
    )
    return mcp_text_result(rows)


async def _tool_get_random_fact(request: Request, args: dict[str, Any]) -> dict[str, Any]:
    category = _get_optional_str(args, "category")
    fact = await get_random_fact(request.app.state.db, category=category)
    if not fact:
        return mcp_text_result({"message": "No facts available yet. Submit some!"})
    return mcp_text_result(fact)


async def _tool_list_facts(request: Request, args: dict[str, Any]) -> dict[str, Any]:
    limit = _get_limit(args)
    category = _get_optional_str(args, "category")
    rows = await get_all_facts(
        request.app.state.db, category=category, approved_only=True,
    )
    return mcp_text_result(rows[:limit])


async def _tool_get_prediction_leaderboard(request: Request, args: dict[str, Any]) -> dict[str, Any]:
    season = args.get("season", 2025)
    if not isinstance(season, int):
        raise ValueError("'season' must be an integer")
    category = _get_optional_str(args, "category")
    if category not in ("driver_championship", "constructor_championship"):
        raise ValueError("'category' must be 'driver_championship' or 'constructor_championship'")
    rows = await get_prediction_leaderboard(
        request.app.state.db, season=season, category=category,
    )
    return mcp_text_result(rows)


# ── Tool registry ────────────────────────────────────────────────────────────
TOOLS: dict[str, ToolHandler] = {
    "list_drivers": _tool_list_drivers,
    "search_drivers": _tool_search_drivers,
    "get_driver_season_stats": _tool_get_driver_season_stats,
    "list_teams": _tool_list_teams,
    "search_teams": _tool_search_teams,
    "list_circuits": _tool_list_circuits,
    "search_circuits": _tool_search_circuits,
    "list_seasons": _tool_list_seasons,
    "list_races": _tool_list_races,
    "list_race_results": _tool_list_race_results,
    "get_random_fact": _tool_get_random_fact,
    "list_facts": _tool_list_facts,
    "get_prediction_leaderboard": _tool_get_prediction_leaderboard,
}


# ── Tool definitions (JSON Schema for MCP clients) ──────────────────────────
def get_tool_definitions() -> list[dict[str, Any]]:
    """Return the MCP ``tools/list`` response payload."""
    return [
        # ── Drivers ──────────────────────────────────────────────────────
        {
            "name": "list_drivers",
            "description": "List F1 drivers. Mirrors GET /drivers.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "active_only": {
                        "type": "boolean",
                        "default": False,
                        "description": "Only return active drivers.",
                    },
                    "limit": LIMIT_SCHEMA,
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "search_drivers",
            "description": "Search drivers by name and/or team. Mirrors GET /drivers/search.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": _DESC_PARTIAL_NAME},
                    "team": {"type": "string", "description": "Partial team match."},
                    "limit": LIMIT_SCHEMA,
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "get_driver_season_stats",
            "description": (
                "Get aggregated season performance stats for drivers "
                "(wins, podiums, points, championship position). "
                "Mirrors GET /drivers/stats/season/{season_year}."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "season_year": {"type": "integer", "description": "Championship year."},
                    "driver_id": {"type": "integer", "description": "Kaggle driver id."},
                    "limit": LIMIT_SCHEMA,
                },
                "additionalProperties": False,
            },
        },
        # ── Teams ────────────────────────────────────────────────────────
        {
            "name": "list_teams",
            "description": "List F1 teams / constructors. Mirrors GET /teams.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "active_only": {
                        "type": "boolean",
                        "default": False,
                        "description": "Only return active teams.",
                    },
                    "limit": LIMIT_SCHEMA,
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "search_teams",
            "description": "Search teams by name. Mirrors GET /teams/search.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": _DESC_PARTIAL_NAME},
                    "limit": LIMIT_SCHEMA,
                },
                "additionalProperties": False,
            },
        },
        # ── Circuits ─────────────────────────────────────────────────────
        {
            "name": "list_circuits",
            "description": "List F1 circuits / venues. Mirrors GET /circuits.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "active_only": {
                        "type": "boolean",
                        "default": False,
                        "description": "Only return currently active circuits.",
                    },
                    "country": {"type": "string", "description": "Filter by country."},
                    "limit": LIMIT_SCHEMA,
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "search_circuits",
            "description": "Search circuits by name and/or country. Mirrors GET /circuits/search.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": _DESC_PARTIAL_NAME},
                    "country": {"type": "string", "description": _DESC_PARTIAL_COUNTRY},
                    "limit": LIMIT_SCHEMA,
                },
                "additionalProperties": False,
            },
        },
        # ── Seasons ──────────────────────────────────────────────────────
        {
            "name": "list_seasons",
            "description": (
                "List F1 championship seasons (newest first). "
                "Mirrors GET /seasons."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "start_year": {"type": "integer", "description": "Start year (inclusive)."},
                    "end_year": {"type": "integer", "description": "End year (inclusive)."},
                    "limit": LIMIT_SCHEMA,
                },
                "additionalProperties": False,
            },
        },
        # ── Races ────────────────────────────────────────────────────────
        {
            "name": "list_races",
            "description": "List races filtered by season year and/or circuit id. Mirrors GET /races.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "season_year": {"type": "integer", "description": "Championship year."},
                    "circuit_id": {"type": "integer", "description": "Kaggle circuit id."},
                    "limit": LIMIT_SCHEMA,
                },
                "additionalProperties": False,
            },
        },
        # ── Results ──────────────────────────────────────────────────────
        {
            "name": "list_race_results",
            "description": (
                "List race results with flexible filtering. "
                "Mirrors GET /results/race."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "race_id": {"type": "integer", "description": "Filter by race id."},
                    "season_year": {"type": "integer", "description": "Filter by season year."},
                    "driver_id": {"type": "integer", "description": "Filter by Kaggle driver id."},
                    "constructor_id": {"type": "integer", "description": "Filter by Kaggle constructor id."},
                    "limit": LIMIT_SCHEMA,
                },
                "additionalProperties": False,
            },
        },
        # ── Trivia / Facts ───────────────────────────────────────────────
        {
            "name": "get_random_fact",
            "description": "Get a random approved F1 fact. Mirrors GET /trivia/random.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Category filter: history, records, fun, technical.",
                    },
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "list_facts",
            "description": "List all approved F1 facts. Mirrors GET /trivia.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Category filter."},
                    "limit": LIMIT_SCHEMA,
                },
                "additionalProperties": False,
            },
        },
        # ── Prediction leaderboard ───────────────────────────────────────
        {
            "name": "get_prediction_leaderboard",
            "description": (
                "Community prediction leaderboard — who does the community "
                "think will win? Mirrors GET /predictions/leaderboard/drivers "
                "and /predictions/leaderboard/constructors."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "season": {"type": "integer", "default": 2025, "description": "Season year."},
                    "category": {
                        "type": "string",
                        "enum": ["driver_championship", "constructor_championship"],
                        "description": "Championship category.",
                    },
                },
                "required": ["category"],
                "additionalProperties": False,
            },
        },
    ]
