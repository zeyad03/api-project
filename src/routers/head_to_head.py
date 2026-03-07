"""Head-to-head router – compare two drivers & vote on who's better."""

from fastapi import APIRouter, Depends, Request, status

from src.core.security import get_current_user
from src.db.drivers import get_driver_by_id
from src.db.head_to_head import cast_h2h_vote, get_h2h_results
from src.models.head_to_head import (
    HeadToHeadComparison,
    HeadToHeadVote,
    HeadToHeadVoteCreate,
)
from src.models.user import TokenData

router = APIRouter()


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

    One vote per user per matchup (can change your vote).
    """
    return await cast_h2h_vote(current_user.user_id, body, request.app.state.db)
