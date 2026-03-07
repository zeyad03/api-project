"""Predictions router – submit, update, delete predictions & view leaderboard."""

from fastapi import APIRouter, Depends, Query, Request, status

from src.core.security import get_current_user
from src.db.predictions import (
    create_prediction_db,
    delete_prediction_db,
    get_prediction_by_id,
    get_prediction_leaderboard,
    get_user_predictions,
    update_prediction_db,
)
from src.models.common import StatusResponse
from src.models.prediction import (
    LeaderboardEntry,
    Prediction,
    PredictionCreate,
    PredictionUpdate,
)
from src.models.user import TokenData

router = APIRouter()


# ── My predictions ───────────────────────────────────────────────────────────
@router.get("", response_model=list[Prediction])
async def list_my_predictions(
    request: Request,
    current_user: TokenData = Depends(get_current_user),
    season: int | None = Query(None),
    category: str | None = Query(None),
):
    """List the authenticated user's predictions."""
    return await get_user_predictions(
        current_user.user_id, request.app.state.db,
        season=season, category=category,
    )


# ── Get single prediction ───────────────────────────────────────────────────
@router.get("/view/{pred_id}", response_model=Prediction)
async def get_prediction(
    pred_id: str,
    request: Request,
    _: TokenData = Depends(get_current_user),
):
    """Get a single prediction by ID."""
    return await get_prediction_by_id(pred_id, request.app.state.db)


# ── Submit a prediction ─────────────────────────────────────────────────────
@router.post("", response_model=Prediction, status_code=status.HTTP_201_CREATED)
async def create_prediction(
    body: PredictionCreate,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Submit a championship prediction (one per category per season)."""
    return await create_prediction_db(
        current_user.user_id, body, request.app.state.db
    )


# ── Update a prediction ─────────────────────────────────────────────────────
@router.patch("/{pred_id}", response_model=Prediction)
async def update_prediction(
    pred_id: str,
    body: PredictionUpdate,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Update your prediction (change pick, confidence, reasoning)."""
    return await update_prediction_db(
        pred_id, current_user.user_id, body, request.app.state.db
    )


# ── Delete a prediction ─────────────────────────────────────────────────────
@router.delete("/{pred_id}", response_model=StatusResponse)
async def delete_prediction(
    pred_id: str,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Delete one of your predictions."""
    await delete_prediction_db(pred_id, current_user.user_id, request.app.state.db)
    return StatusResponse(status="ok", message="Prediction deleted")


# ── Global leaderboard (public) ─────────────────────────────────────────────
@router.get("/leaderboard/drivers", response_model=list[LeaderboardEntry])
async def driver_championship_leaderboard(
    request: Request,
    season: int = Query(2025, description="Season year"),
):
    """Who does the community think will win the Drivers' Championship?"""
    return await get_prediction_leaderboard(
        request.app.state.db, season=season, category="driver_championship"
    )


@router.get("/leaderboard/constructors", response_model=list[LeaderboardEntry])
async def constructor_championship_leaderboard(
    request: Request,
    season: int = Query(2025, description="Season year"),
):
    """Who does the community think will win the Constructors' Championship?"""
    return await get_prediction_leaderboard(
        request.app.state.db, season=season, category="constructor_championship"
    )
