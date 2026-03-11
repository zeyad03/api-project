"""Races router – browse F1 race calendar and status data."""

from fastapi import APIRouter, HTTPException, Query, Request, status

from src.db.races import get_all_races, get_all_statuses, get_race_by_id, get_race_by_season_round
from src.models.race import Race, Status

router = APIRouter()


@router.get("", response_model=list[Race])
async def list_races(
    request: Request,
    season_year: int | None = Query(None, description="Filter by season year"),
    circuit_id: int | None = Query(None, description="Filter by circuit id"),
):
    """List races, optionally filtered by season year or circuit."""
    return await get_all_races(
        request.app.state.db, season_year=season_year, circuit_id=circuit_id
    )


@router.get("/statuses", response_model=list[Status])
async def list_statuses(request: Request):
    """List all race finish status codes."""
    return await get_all_statuses(request.app.state.db)


@router.get("/{race_id}", response_model=Race)
async def get_race(race_id: int, request: Request):
    """Get a single race by its Kaggle raceId."""
    race = await get_race_by_id(race_id, request.app.state.db)
    if not race:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Race with id '{race_id}' was not found.",
        )
    return race


@router.get("/season/{season_year}/round/{round_number}", response_model=Race)
async def get_race_by_round(season_year: int, round_number: int, request: Request):
    """Get a race by season year and round number."""
    race = await get_race_by_season_round(season_year, round_number, request.app.state.db)
    if not race:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Race for season {season_year}, round {round_number} was not found.",
        )
    return race
