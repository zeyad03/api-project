"""Head-to-head router – compare two drivers & vote on who's better."""

from fastapi import APIRouter, Depends, Request, status

from src.core.security import get_current_user
from src.db.drivers import get_driver_by_id, get_driver_by_name
from src.db.head_to_head import cast_h2h_vote, get_h2h_results
from src.core.exceptions import BadRequestError
from src.models.head_to_head import (
    HeadToHeadComparison,
    HeadToHeadVote,
    HeadToHeadVoteCreate,
)
from src.models.user import TokenData

router = APIRouter()


async def _resolve_driver_id(
    *, driver_id: str | None, driver_name: str | None, db, label: str
) -> str:
    """Return a driver ID from either an explicit ID or a name lookup."""
    if driver_id:
        return driver_id
    if driver_name:
        driver = await get_driver_by_name(driver_name, db)
        return str(driver.id)
    raise BadRequestError(f"Provide either {label}_id or {label}_name")


@router.get("/compare/{driver1_id}/{driver2_id}", response_model=HeadToHeadComparison)
async def compare_drivers(
    driver1_id: str, driver2_id: str, request: Request
):
    """Compare two drivers' stats side-by-side with community vote results."""
    db = request.app.state.db
    d1 = await get_driver_by_id(driver1_id, db)
    d2 = await get_driver_by_id(driver2_id, db)
    votes = await get_h2h_results(driver1_id, driver2_id, db)
    return HeadToHeadComparison(
        driver1=d1.model_dump(),
        driver2=d2.model_dump(),
        community_votes=votes,
    )


@router.post("/vote", response_model=HeadToHeadVote, status_code=status.HTTP_201_CREATED)
async def vote_head_to_head(
    body: HeadToHeadVoteCreate,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Vote for your preferred driver in a head-to-head matchup.

    Supply driver IDs **or** driver names (or a mix) for driver1, driver2,
    and winner.  One vote per user per matchup (can change your vote).
    """
    db = request.app.state.db
    body.driver1_id = await _resolve_driver_id(
        driver_id=body.driver1_id, driver_name=body.driver1_name,
        db=db, label="driver1",
    )
    body.driver2_id = await _resolve_driver_id(
        driver_id=body.driver2_id, driver_name=body.driver2_name,
        db=db, label="driver2",
    )
    body.winner_id = await _resolve_driver_id(
        driver_id=body.winner_id, driver_name=body.winner_name,
        db=db, label="winner",
    )
    return await cast_h2h_vote(current_user.user_id, body, db)
