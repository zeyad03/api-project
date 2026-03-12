"""Seasons router – browse F1 championship season data."""

from fastapi import APIRouter, Query, Request

from src.core.exceptions import NotFoundError
from src.db.seasons import get_all_seasons, get_season_by_year, get_seasons_range
from src.models.common import PaginatedResponse
from src.models.season import Season

router = APIRouter()


@router.get("", response_model=PaginatedResponse[Season])
async def list_seasons(
    request: Request,
    start_year: int | None = Query(None, description="Start year (inclusive)"),
    end_year: int | None = Query(None, description="End year (inclusive)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=200, description="Max records to return"),
):
    """List all F1 seasons, optionally filtered by year range. Newest first."""
    if start_year is not None or end_year is not None:
        seasons = await get_seasons_range(
            request.app.state.db, start_year=start_year, end_year=end_year
        )
        return PaginatedResponse(data=seasons, total=len(seasons), skip=0, limit=len(seasons))
    seasons, total = await get_all_seasons(
        request.app.state.db, skip=skip, limit=limit
    )
    return PaginatedResponse(data=seasons, total=total, skip=skip, limit=limit)


@router.get("/{year}", response_model=Season)
async def get_season(year: int, request: Request):
    """Get a single season by championship year."""
    season = await get_season_by_year(year, request.app.state.db)
    if not season:
        raise NotFoundError("Season", str(year))
    return season
