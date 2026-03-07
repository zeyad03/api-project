"""Teams router – CRUD for F1 team / constructor data."""

from fastapi import APIRouter, Depends, Query, Request, status

from src.core.security import get_current_user, require_admin
from src.db.teams import (
    create_team_db,
    delete_team_db,
    get_all_teams,
    get_team_by_id,
    search_teams,
    update_team_db,
)
from src.models.common import StatusResponse
from src.models.team import Team, TeamCreate, TeamUpdate
from src.models.user import TokenData

router = APIRouter()


@router.get("", response_model=list[Team])
async def list_teams(
    request: Request,
    active_only: bool = Query(False, description="Only return active teams"),
):
    """List all F1 teams. No auth required."""
    return await get_all_teams(request.app.state.db, active_only=active_only)


@router.get("/search", response_model=list[Team])
async def search(request: Request, name: str | None = Query(None)):
    """Search teams by name (case-insensitive partial match)."""
    return await search_teams(request.app.state.db, name=name)


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
