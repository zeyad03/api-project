"""Seasons router – browse F1 championship season data."""

from fastapi import APIRouter, HTTPException, Query, Request, status

from src.db.seasons import get_all_seasons, get_season_by_year, get_seasons_range
from src.models.season import Season

router = APIRouter()


@router.get("", response_model=list[Season])
async def list_seasons(
    request: Request,
    start_year: int | None = Query(None, description="Start year (inclusive)"),
    end_year: int | None = Query(None, description="End year (inclusive)"),
):
    """List all F1 seasons, optionally filtered by year range. Newest first."""
    if start_year is not None or end_year is not None:
        return await get_seasons_range(
            request.app.state.db, start_year=start_year, end_year=end_year
        )
    return await get_all_seasons(request.app.state.db)


@router.get("/{year}", response_model=Season)
async def get_season(year: int, request: Request):
    """Get a single season by championship year."""
    season = await get_season_by_year(year, request.app.state.db)
    if not season:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Season {year} was not found.",
        )
    return season
