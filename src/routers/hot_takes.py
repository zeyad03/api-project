"""Hot Takes router – post and react to controversial F1 opinions."""

from fastapi import APIRouter, Depends, Query, Request, status

from src.core.security import get_current_user
from src.db.hot_takes import (
    create_hot_take_db,
    delete_hot_take_db,
    get_all_hot_takes,
    get_hot_take_by_id,
    react_to_hot_take,
)
from src.db.users import get_user_by_id
from src.models.common import StatusResponse
from src.models.hot_take import HotTake, HotTakeCreate, HotTakeReaction
from src.models.user import TokenData

router = APIRouter()


@router.get("", response_model=list[HotTake])
async def list_hot_takes(
    request: Request,
    category: str | None = Query(None),
    sort_by: str = Query("recent", pattern="^(recent|spicy|popular)$"),
):
    """List hot takes. Sort: recent, spicy (most disagreed), popular (most agreed)."""
    return await get_all_hot_takes(
        request.app.state.db, category=category, sort_by=sort_by
    )


@router.get("/{take_id}", response_model=HotTake)
async def get_hot_take(take_id: str, request: Request):
    """Get a single hot take."""
    return await get_hot_take_by_id(take_id, request.app.state.db)


@router.post("", response_model=HotTake, status_code=status.HTTP_201_CREATED)
async def post_hot_take(
    body: HotTakeCreate,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Post a controversial F1 opinion."""
    db = request.app.state.db
    user = await get_user_by_id(current_user.user_id, db)
    return await create_hot_take_db(
        current_user.user_id, user.display_name, body, db
    )


@router.post("/{take_id}/react", response_model=HotTake)
async def react(
    take_id: str,
    body: HotTakeReaction,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Agree or disagree with a hot take (toggleable)."""
    return await react_to_hot_take(
        take_id, current_user.user_id, body.reaction, request.app.state.db
    )


@router.delete("/{take_id}", response_model=StatusResponse)
async def delete_hot_take(
    take_id: str,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Delete your own hot take (admins can delete any)."""
    await delete_hot_take_db(
        take_id, current_user.user_id, request.app.state.db,
        is_admin=current_user.is_admin,
    )
    return StatusResponse(status="ok", message="Hot take deleted")
