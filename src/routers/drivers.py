"""Drivers router – CRUD for F1 driver data plus season statistics."""

from fastapi import APIRouter, Depends, Query, Request, status

from src.core.security import get_current_user, require_admin
from src.db.drivers import (
    create_driver_db,
    delete_driver_db,
    get_all_drivers,
    get_driver_by_id,
    get_driver_season_stats,
    get_driver_stats_by_mongo_id,
    search_drivers,
    update_driver_db,
)
from src.models.common import StatusResponse
from src.models.driver import Driver, DriverCreate, DriverSeasonStat, DriverUpdate
from src.models.user import TokenData

router = APIRouter()


@router.get("", response_model=list[Driver])
async def list_drivers(
    request: Request,
    active_only: bool = Query(False, description="Only return active drivers"),
):
    """List all F1 drivers. No auth required."""
    return await get_all_drivers(request.app.state.db, active_only=active_only)


@router.get("/search", response_model=list[Driver])
async def search(
    request: Request,
    name: str | None = Query(None),
    team: str | None = Query(None),
):
    """Search drivers by name or team (case-insensitive partial match)."""
    return await search_drivers(request.app.state.db, name=name, team=team)


@router.get("/{driver_id}", response_model=Driver)
async def get_driver(driver_id: str, request: Request):
    """Get a single driver by ID."""
    return await get_driver_by_id(driver_id, request.app.state.db)


@router.post("", response_model=Driver, status_code=status.HTTP_201_CREATED)
async def create_driver(
    body: DriverCreate,
    request: Request,
    _: TokenData = Depends(require_admin),
):
    """Create a new driver (admin only)."""
    return await create_driver_db(body, request.app.state.db)


@router.patch("/{driver_id}", response_model=Driver)
async def update_driver(
    driver_id: str,
    body: DriverUpdate,
    request: Request,
    _: TokenData = Depends(require_admin),
):
    """Update a driver's details (admin only)."""
    return await update_driver_db(driver_id, body, request.app.state.db)


@router.delete("/{driver_id}", response_model=StatusResponse)
async def delete_driver(
    driver_id: str,
    request: Request,
    _: TokenData = Depends(require_admin),
):
    """Delete a driver (admin only)."""
    await delete_driver_db(driver_id, request.app.state.db)
    return StatusResponse(status="ok", message="Driver deleted")


# ── Season statistics ────────────────────────────────────────────────────────

@router.get("/{driver_id}/stats", response_model=list[DriverSeasonStat])
async def driver_season_stats(
    driver_id: str,
    request: Request,
    season_year: int | None = Query(None, description="Filter to a specific season"),
):
    """Get historical season stats for a driver (by MongoDB _id).

    Returns aggregated season performance data including wins, podiums,
    points, and championship positions across all seasons.
    """
    stats = await get_driver_stats_by_mongo_id(driver_id, request.app.state.db)
    if season_year is not None:
        stats = [s for s in stats if s.season_year == season_year]
    return stats


@router.get("/stats/season/{season_year}", response_model=list[DriverSeasonStat])
async def all_driver_stats_for_season(season_year: int, request: Request):
    """Get all driver season stats for a given championship year."""
    return await get_driver_season_stats(
        request.app.state.db, season_year=season_year
    )
