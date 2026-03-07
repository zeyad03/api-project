"""Drivers router – CRUD for F1 driver data."""

from fastapi import APIRouter, Depends, Query, Request, status

from src.core.security import get_current_user, require_admin
from src.db.drivers import (
    create_driver_db,
    delete_driver_db,
    get_all_drivers,
    get_driver_by_id,
    search_drivers,
    update_driver_db,
)
from src.models.common import StatusResponse
from src.models.driver import Driver, DriverCreate, DriverUpdate
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
