"""Results router – browse race results, sprint results, and lap-time data."""

from fastapi import APIRouter, Query, Request

from src.db.results import get_lap_time_summaries, get_race_results, get_sprint_results
from src.models.result import LapTimeSummary, RaceResult, SprintResult

router = APIRouter()


@router.get("/race", response_model=list[RaceResult])
async def list_race_results(
    request: Request,
    race_id: int | None = Query(None, description="Filter by race id"),
    season_year: int | None = Query(None, description="Filter by season year"),
    driver_id: int | None = Query(None, description="Filter by Kaggle driver id"),
    constructor_id: int | None = Query(None, description="Filter by Kaggle constructor id"),
    limit: int = Query(100, ge=1, le=1000, description="Max results to return"),
):
    """List race results with flexible filtering."""
    return await get_race_results(
        request.app.state.db,
        race_id=race_id,
        season_year=season_year,
        driver_id=driver_id,
        constructor_id=constructor_id,
        limit=limit,
    )


@router.get("/sprint", response_model=list[SprintResult])
async def list_sprint_results(
    request: Request,
    race_id: int | None = Query(None, description="Filter by race id"),
    season_year: int | None = Query(None, description="Filter by season year"),
    driver_id: int | None = Query(None, description="Filter by Kaggle driver id"),
    limit: int = Query(100, ge=1, le=1000, description="Max results to return"),
):
    """List sprint results with flexible filtering."""
    return await get_sprint_results(
        request.app.state.db,
        race_id=race_id,
        season_year=season_year,
        driver_id=driver_id,
        limit=limit,
    )


@router.get("/lap-times", response_model=list[LapTimeSummary])
async def list_lap_time_summaries(
    request: Request,
    race_id: int | None = Query(None, description="Filter by race id"),
    driver_id: int | None = Query(None, description="Filter by Kaggle driver id"),
    season_year: int | None = Query(None, description="Filter by season year"),
    limit: int = Query(100, ge=1, le=1000, description="Max results to return"),
):
    """List lap-time summaries with flexible filtering."""
    return await get_lap_time_summaries(
        request.app.state.db,
        race_id=race_id,
        driver_id=driver_id,
        season_year=season_year,
        limit=limit,
    )
