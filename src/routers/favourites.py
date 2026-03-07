"""Favourites router – manage personal favourite-driver / favourite-team lists."""

from fastapi import APIRouter, Depends, Query, Request, status

from src.core.security import get_current_user
from src.db.favourites import (
    add_item_to_favourite,
    create_favourite_db,
    delete_favourite_db,
    get_favourite_by_id,
    get_user_favourites,
    remove_item_from_favourite,
    update_favourite_db,
)
from src.models.common import StatusResponse
from src.models.favourite import (
    AddFavouriteItem,
    FavouriteList,
    FavouriteListCreate,
    FavouriteListUpdate,
)
from src.models.user import TokenData

router = APIRouter()


# ── List all my favourite lists ──────────────────────────────────────────────
@router.get("", response_model=list[FavouriteList])
async def list_favourites(
    request: Request,
    current_user: TokenData = Depends(get_current_user),
    list_type: str | None = Query(None, pattern="^(drivers|teams)$"),
):
    """Return all favourite lists for the authenticated user."""
    return await get_user_favourites(
        current_user.user_id, request.app.state.db, list_type=list_type
    )


# ── Get a specific list ─────────────────────────────────────────────────────
@router.get("/{fav_id}", response_model=FavouriteList)
async def get_favourite(
    fav_id: str,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Get a single favourite list by ID."""
    return await get_favourite_by_id(fav_id, current_user.user_id, request.app.state.db)


# ── Create a new list ───────────────────────────────────────────────────────
@router.post("", response_model=FavouriteList, status_code=status.HTTP_201_CREATED)
async def create_favourite(
    body: FavouriteListCreate,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Create a new favourite list (e.g. 'My Top Drivers')."""
    return await create_favourite_db(
        current_user.user_id, body, request.app.state.db
    )


# ── Update list metadata ────────────────────────────────────────────────────
@router.patch("/{fav_id}", response_model=FavouriteList)
async def update_favourite(
    fav_id: str,
    body: FavouriteListUpdate,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Rename a favourite list."""
    return await update_favourite_db(
        fav_id, current_user.user_id, body, request.app.state.db
    )


# ── Delete a list ────────────────────────────────────────────────────────────
@router.delete("/{fav_id}", response_model=StatusResponse)
async def delete_favourite(
    fav_id: str,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Delete a favourite list."""
    await delete_favourite_db(fav_id, current_user.user_id, request.app.state.db)
    return StatusResponse(status="ok", message="Favourite list deleted")


# ── Add item to list ────────────────────────────────────────────────────────
@router.post("/{fav_id}/items", response_model=FavouriteList)
async def add_item(
    fav_id: str,
    body: AddFavouriteItem,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Add a driver or team to a favourite list."""
    return await add_item_to_favourite(
        fav_id, current_user.user_id, body, request.app.state.db
    )


# ── Remove item from list ───────────────────────────────────────────────────
@router.delete("/{fav_id}/items/{item_id}", response_model=FavouriteList)
async def remove_item(
    fav_id: str,
    item_id: str,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Remove a driver or team from a favourite list."""
    return await remove_item_from_favourite(
        fav_id, current_user.user_id, item_id, request.app.state.db
    )
