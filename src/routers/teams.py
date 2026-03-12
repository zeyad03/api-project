"""Teams router – CRUD for F1 team / constructor data plus season statistics."""

from fastapi import APIRouter, Depends, Query, Request, status

from src.core.security import get_current_user, require_admin
from src.db.teams import (
    create_team_db,
    delete_team_db,
    get_all_teams,
    get_constructor_results,
    get_constructor_season_stats,
    get_constructor_standings,
    get_team_by_id,
    get_team_stats_by_mongo_id,
    search_teams,
    update_team_db,
)
from src.models.common import PaginatedResponse, StatusResponse
from src.models.team import (
    ConstructorResult,
    ConstructorSeasonStat,
    ConstructorStanding,
    Team,
    TeamCreate,
    TeamUpdate,
)
from src.models.user import TokenData

router = APIRouter()


@router.get("", response_model=PaginatedResponse[Team])
async def list_teams(
    request: Request,
    active_only: bool = Query(False, description="Only return active teams"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=200, description="Max records to return"),
):
    """List all F1 teams. No auth required."""
    teams, total = await get_all_teams(
        request.app.state.db, active_only=active_only, skip=skip, limit=limit
    )
    return PaginatedResponse(data=teams, total=total, skip=skip, limit=limit)


@router.get("/search", response_model=PaginatedResponse[Team])
async def search(
    request: Request,
    name: str | None = Query(None),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=200, description="Max records to return"),
):
    """Search teams by name (case-insensitive partial match)."""
    teams, total = await search_teams(
        request.app.state.db, name=name, skip=skip, limit=limit
    )
    return PaginatedResponse(data=teams, total=total, skip=skip, limit=limit)


@router.get("/{team_id}", response_model=Team)
async def get_team(team_id: str, request: Request):
    """Get a single team by ID."""
    return await get_team_by_id(team_id, request.app.state.db)


@router.post("", response_model=Team, status_code=status.HTTP_201_CREATED)
async def create_team(
    body: TeamCreate,
    request: Request,
    _: TokenData = Depends(require_admin),
):
    """Create a new team (admin only)."""
    return await create_team_db(body, request.app.state.db)


@router.patch("/{team_id}", response_model=Team)
async def update_team(
    team_id: str,
    body: TeamUpdate,
    request: Request,
    _: TokenData = Depends(require_admin),
):
    """Update a team's details (admin only)."""
    return await update_team_db(team_id, body, request.app.state.db)


@router.delete("/{team_id}", response_model=StatusResponse)
async def delete_team(
    team_id: str,
    request: Request,
    _: TokenData = Depends(require_admin),
):
    """Delete a team (admin only)."""
    await delete_team_db(team_id, request.app.state.db)
    return StatusResponse(status="ok", message="Team deleted")


# ── Season statistics & standings ────────────────────────────────────────────

@router.get("/{team_id}/stats", response_model=list[ConstructorSeasonStat])
async def team_season_stats(
    team_id: str,
    request: Request,
    season_year: int | None = Query(None, description="Filter to a specific season"),
):
    """Get historical season stats for a team (by MongoDB _id).

    Returns aggregated season performance data including wins, points,
    podiums, and championship positions across all seasons.
    """
    stats = await get_team_stats_by_mongo_id(team_id, request.app.state.db)
    if season_year is not None:
        stats = [s for s in stats if s.season_year == season_year]
    return stats


@router.get("/stats/season/{season_year}", response_model=list[ConstructorSeasonStat])
async def all_team_stats_for_season(season_year: int, request: Request):
    """Get all constructor season stats for a given championship year."""
    return await get_constructor_season_stats(
        request.app.state.db, season_year=season_year
    )


@router.get("/{team_id}/standings", response_model=list[ConstructorStanding])
async def team_standings(
    team_id: str,
    request: Request,
    season_year: int | None = Query(None, description="Filter to a specific season"),
    final_only: bool = Query(False, description="Only return end-of-season standings"),
):
    """Get constructor championship standings history for a team."""
    team = await get_team_by_id(team_id, request.app.state.db)
    if team.kaggle_constructor_id == 0:
        return []
    return await get_constructor_standings(
        request.app.state.db,
        constructor_id=team.kaggle_constructor_id,
        season_year=season_year,
        final_only=final_only,
    )


@router.get("/{team_id}/results", response_model=list[ConstructorResult])
async def team_results(
    team_id: str,
    request: Request,
    season_year: int | None = Query(None, description="Filter to a specific season"),
):
    """Get constructor race results history for a team."""
    team = await get_team_by_id(team_id, request.app.state.db)
    if team.kaggle_constructor_id == 0:
        return []
    return await get_constructor_results(
        request.app.state.db,
        constructor_id=team.kaggle_constructor_id,
        season_year=season_year,
    )
