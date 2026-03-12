"""Races router – browse F1 race calendar and status data."""

from fastapi import APIRouter, Query, Request

from src.core.exceptions import NotFoundError
from src.db.races import get_all_races, get_all_statuses, get_race_by_id, get_race_by_season_round
from src.models.common import PaginatedResponse
from src.models.race import Race, Status

router = APIRouter()


@router.get("", response_model=PaginatedResponse[Race])
async def list_races(
    request: Request,
    season_year: int | None = Query(None, description="Filter by season year"),
    circuit_id: int | None = Query(None, description="Filter by circuit id"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=200, description="Max records to return"),
):
    """List races, optionally filtered by season year or circuit."""
    races, total = await get_all_races(
        request.app.state.db, season_year=season_year, circuit_id=circuit_id,
        skip=skip, limit=limit,
    )
    return PaginatedResponse(data=races, total=total, skip=skip, limit=limit)


@router.get("/statuses", response_model=list[Status])
async def list_statuses(request: Request):
    """List all race finish status codes."""
    return await get_all_statuses(request.app.state.db)


@router.get("/{race_id}", response_model=Race)
async def get_race(race_id: int, request: Request):
    """Get a single race by its Kaggle raceId."""
    race = await get_race_by_id(race_id, request.app.state.db)
    if not race:
        raise NotFoundError("Race", str(race_id))
    return race


@router.get("/season/{season_year}/round/{round_number}", response_model=Race)
async def get_race_by_round(season_year: int, round_number: int, request: Request):
    """Get a race by season year and round number."""
    race = await get_race_by_season_round(season_year, round_number, request.app.state.db)
    if not race:
        raise NotFoundError("Race", f"season {season_year}, round {round_number}")
    return race
