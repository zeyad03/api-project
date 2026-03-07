"""Tests for src/db/ – database query functions with mocked Motor collections."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from bson import ObjectId

from src.core.exceptions import (
    DriverNotFoundError,
    DuplicateFavouriteItemError,
    DuplicatePredictionError,
    EmptyUpdateError,
    FactNotFoundError,
    FavouriteListNotFoundError,
    HotTakeDeleteNotFoundError,
    HotTakeNotFoundError,
    InvalidVoteError,
    PredictionNotFoundError,
    TeamNotFoundError,
    UserNotFoundError,
)

# ── Fake IDs ─────────────────────────────────────────────────────────────────
FID = "507f1f77bcf86cd799439011"
FID2 = "507f1f77bcf86cd799439012"
OID = ObjectId(FID)
OID2 = ObjectId(FID2)
TS = "2025-01-01T00:00:00+00:00"


# ── Async-cursor mock ───────────────────────────────────────────────────────
class _AsyncIter:
    def __init__(self, items):
        self._it = iter(items)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._it)
        except StopIteration:
            raise StopAsyncIteration


class MockCursor(_AsyncIter):
    """Motor cursor mock with chainable sort/limit."""

    def sort(self, *a, **kw):
        return self

    def limit(self, n):
        return self


# ── Helpers ──────────────────────────────────────────────────────────────────
def _col(*, find_one=None, find_docs=None, agg_docs=None,
         inserted_id=OID, matched=1, deleted=1):
    """Build a mocked Motor collection."""
    c = MagicMock()
    c.find_one = AsyncMock(return_value=find_one)
    c.find = MagicMock(return_value=MockCursor(find_docs or []))
    c.insert_one = AsyncMock(return_value=MagicMock(inserted_id=inserted_id))
    c.update_one = AsyncMock(return_value=MagicMock(matched_count=matched))
    c.delete_one = AsyncMock(return_value=MagicMock(deleted_count=deleted))
    c.aggregate = MagicMock(return_value=MockCursor(agg_docs or []))
    return c


def _db(col):
    db = MagicMock()
    db.__getitem__ = MagicMock(return_value=col)
    return db


# ── Document factories ───────────────────────────────────────────────────────
def _driver_doc(**kw):
    d = {"_id": OID, "name": "Lewis Hamilton", "number": 44,
         "team": "Ferrari", "nationality": "British",
         "date_of_birth": "1985-01-07", "championships": 7,
         "wins": 103, "podiums": 197, "poles": 104,
         "bio": "", "active": True, "created_at": TS}
    d.update(kw)
    return d


def _team_doc(**kw):
    d = {"_id": OID, "name": "Ferrari", "full_name": "Scuderia Ferrari",
         "base": "Maranello", "team_principal": "Fred Vasseur",
         "championships": 16, "first_entry": 1950, "car": "SF-25",
         "engine": "Ferrari", "active": True, "created_at": TS}
    d.update(kw)
    return d


def _user_doc(**kw):
    d = {"_id": OID, "username": "testuser", "email": "t@test.com",
         "display_name": "Test User", "is_admin": False,
         "password_hash": "hashed", "created_at": TS}
    d.update(kw)
    return d


def _fact_doc(**kw):
    d = {"_id": OID, "content": "F1 fact content here for testing",
         "category": "fun", "source": "", "submitted_by": "system",
         "approved": True, "likes": 0, "liked_by": [], "created_at": TS}
    d.update(kw)
    return d


def _fav_doc(**kw):
    d = {"_id": OID, "user_id": FID2, "name": "My List",
         "list_type": "drivers", "items": [], "updated_at": TS,
         "created_at": TS}
    d.update(kw)
    return d


def _vote_doc(**kw):
    d = {"_id": OID, "driver1_id": FID, "driver2_id": FID2,
         "user_id": FID, "winner_id": FID, "created_at": TS}
    d.update(kw)
    return d


def _take_doc(**kw):
    d = {"_id": OID, "user_id": FID, "user_display_name": "Tester",
         "content": "This is a hot take for testing purposes",
         "category": "general", "agrees": 0, "disagrees": 0,
         "agreed_by": [], "disagreed_by": [], "created_at": TS}
    d.update(kw)
    return d


def _pred_doc(**kw):
    d = {"_id": OID, "user_id": FID, "season": 2025,
         "category": "driver_championship",
         "predicted_id": FID2, "predicted_name": "Max Verstappen",
         "confidence": 8, "reasoning": "", "created_at": TS}
    d.update(kw)
    return d


# ═════════════════════════════════════════════════════════════════════════════
#  DRIVERS
# ═════════════════════════════════════════════════════════════════════════════
class TestDriversDB:
    @pytest.mark.asyncio
    async def test_get_all_drivers(self):
        from src.db.drivers import get_all_drivers
        db = _db(_col(find_docs=[_driver_doc()]))
        result = await get_all_drivers(db)
        assert len(result) == 1 and result[0].name == "Lewis Hamilton"

    @pytest.mark.asyncio
    async def test_get_all_drivers_active(self):
        from src.db.drivers import get_all_drivers
        c = _col(find_docs=[_driver_doc()])
        db = _db(c)
        await get_all_drivers(db, active_only=True)
        c.find.assert_called_once_with({"active": True})

    @pytest.mark.asyncio
    async def test_get_driver_by_id(self):
        from src.db.drivers import get_driver_by_id
        db = _db(_col(find_one=_driver_doc()))
        d = await get_driver_by_id(FID, db)
        assert d.name == "Lewis Hamilton"

    @pytest.mark.asyncio
    async def test_get_driver_by_id_not_found(self):
        from src.db.drivers import get_driver_by_id
        db = _db(_col(find_one=None))
        with pytest.raises(DriverNotFoundError):
            await get_driver_by_id(FID, db)

    @pytest.mark.asyncio
    async def test_get_driver_by_name(self):
        from src.db.drivers import get_driver_by_name
        db = _db(_col(find_one=_driver_doc()))
        d = await get_driver_by_name("Lewis Hamilton", db)
        assert d.name == "Lewis Hamilton"

    @pytest.mark.asyncio
    async def test_get_driver_by_name_not_found(self):
        from src.db.drivers import get_driver_by_name
        db = _db(_col(find_one=None))
        with pytest.raises(DriverNotFoundError):
            await get_driver_by_name("Nobody", db)

    @pytest.mark.asyncio
    async def test_search_drivers(self):
        from src.db.drivers import search_drivers
        db = _db(_col(find_docs=[_driver_doc()]))
        result = await search_drivers(db, name="Lewis", team="Ferrari")
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_create_driver(self):
        from src.db.drivers import create_driver_db
        from src.models.driver import DriverCreate
        c = _col(find_one=_driver_doc())
        db = _db(c)
        d = await create_driver_db(DriverCreate(name="Lewis Hamilton", number=44, team="Ferrari"), db)
        assert d.name == "Lewis Hamilton"
        c.insert_one.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_driver(self):
        from src.db.drivers import update_driver_db
        from src.models.driver import DriverUpdate
        db = _db(_col(find_one=_driver_doc(wins=104)))
        d = await update_driver_db(FID, DriverUpdate(wins=104), db)
        assert d.wins == 104

    @pytest.mark.asyncio
    async def test_update_driver_empty(self):
        from src.db.drivers import update_driver_db
        from src.models.driver import DriverUpdate
        db = _db(_col())
        with pytest.raises(EmptyUpdateError):
            await update_driver_db(FID, DriverUpdate(), db)

    @pytest.mark.asyncio
    async def test_update_driver_not_found(self):
        from src.db.drivers import update_driver_db
        from src.models.driver import DriverUpdate
        db = _db(_col(find_one=None))
        with pytest.raises(DriverNotFoundError):
            await update_driver_db(FID, DriverUpdate(wins=1), db)

    @pytest.mark.asyncio
    async def test_delete_driver(self):
        from src.db.drivers import delete_driver_db
        assert await delete_driver_db(FID, _db(_col())) is True

    @pytest.mark.asyncio
    async def test_delete_driver_not_found(self):
        from src.db.drivers import delete_driver_db
        db = _db(_col(deleted=0))
        with pytest.raises(DriverNotFoundError):
            await delete_driver_db(FID, db)


# ═════════════════════════════════════════════════════════════════════════════
#  TEAMS
# ═════════════════════════════════════════════════════════════════════════════
class TestTeamsDB:
    @pytest.mark.asyncio
    async def test_get_all_teams(self):
        from src.db.teams import get_all_teams
        db = _db(_col(find_docs=[_team_doc()]))
        assert len(await get_all_teams(db)) == 1

    @pytest.mark.asyncio
    async def test_get_all_teams_active(self):
        from src.db.teams import get_all_teams
        c = _col(find_docs=[_team_doc()])
        db = _db(c)
        await get_all_teams(db, active_only=True)
        c.find.assert_called_once_with({"active": True})

    @pytest.mark.asyncio
    async def test_get_team_by_id(self):
        from src.db.teams import get_team_by_id
        db = _db(_col(find_one=_team_doc()))
        assert (await get_team_by_id(FID, db)).name == "Ferrari"

    @pytest.mark.asyncio
    async def test_get_team_by_id_not_found(self):
        from src.db.teams import get_team_by_id
        db = _db(_col(find_one=None))
        with pytest.raises(TeamNotFoundError):
            await get_team_by_id(FID, db)

    @pytest.mark.asyncio
    async def test_search_teams(self):
        from src.db.teams import search_teams
        db = _db(_col(find_docs=[_team_doc()]))
        assert len(await search_teams(db, name="Ferrari")) == 1

    @pytest.mark.asyncio
    async def test_create_team(self):
        from src.db.teams import create_team_db
        from src.models.team import TeamCreate
        c = _col(find_one=_team_doc())
        db = _db(c)
        t = await create_team_db(TeamCreate(name="Ferrari"), db)
        assert t.name == "Ferrari"
        c.insert_one.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_team(self):
        from src.db.teams import update_team_db
        from src.models.team import TeamUpdate
        db = _db(_col(find_one=_team_doc()))
        t = await update_team_db(FID, TeamUpdate(championships=17), db)
        assert t.name == "Ferrari"

    @pytest.mark.asyncio
    async def test_update_team_empty(self):
        from src.db.teams import update_team_db
        from src.models.team import TeamUpdate
        with pytest.raises(EmptyUpdateError):
            await update_team_db(FID, TeamUpdate(), _db(_col()))

    @pytest.mark.asyncio
    async def test_update_team_not_found(self):
        from src.db.teams import update_team_db
        from src.models.team import TeamUpdate
        db = _db(_col(find_one=None))
        with pytest.raises(TeamNotFoundError):
            await update_team_db(FID, TeamUpdate(championships=1), db)

    @pytest.mark.asyncio
    async def test_delete_team(self):
        from src.db.teams import delete_team_db
        assert await delete_team_db(FID, _db(_col())) is True

    @pytest.mark.asyncio
    async def test_delete_team_not_found(self):
        from src.db.teams import delete_team_db
        with pytest.raises(TeamNotFoundError):
            await delete_team_db(FID, _db(_col(deleted=0)))


# ═════════════════════════════════════════════════════════════════════════════
#  USERS
# ═════════════════════════════════════════════════════════════════════════════
class TestUsersDB:
    @pytest.mark.asyncio
    async def test_get_user_by_id(self):
        from src.db.users import get_user_by_id
        db = _db(_col(find_one=_user_doc()))
        u = await get_user_by_id(FID, db)
        assert u.username == "testuser"

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self):
        from src.db.users import get_user_by_id
        with pytest.raises(UserNotFoundError):
            await get_user_by_id(FID, _db(_col(find_one=None)))

    @pytest.mark.asyncio
    async def test_get_user_by_username_found(self):
        from src.db.users import get_user_by_username
        db = _db(_col(find_one=_user_doc()))
        u = await get_user_by_username("testuser", db)
        assert u is not None and u.username == "testuser"

    @pytest.mark.asyncio
    async def test_get_user_by_username_none(self):
        from src.db.users import get_user_by_username
        assert await get_user_by_username("nope", _db(_col(find_one=None))) is None

    @pytest.mark.asyncio
    async def test_get_user_by_email_found(self):
        from src.db.users import get_user_by_email
        db = _db(_col(find_one=_user_doc()))
        assert (await get_user_by_email("t@test.com", db)) is not None

    @pytest.mark.asyncio
    async def test_get_user_by_email_none(self):
        from src.db.users import get_user_by_email
        assert await get_user_by_email("x@x.com", _db(_col(find_one=None))) is None

    @pytest.mark.asyncio
    async def test_create_user(self):
        from src.db.users import create_user_db
        c = _col(find_one=_user_doc())
        db = _db(c)
        u = await create_user_db({"username": "testuser"}, db)
        assert u.username == "testuser"

    @pytest.mark.asyncio
    async def test_update_user(self):
        from src.db.users import update_user_db
        from src.models.user import UserUpdate
        db = _db(_col(find_one=_user_doc()))
        u = await update_user_db(FID, UserUpdate(display_name="New"), db)
        assert u.username == "testuser"

    @pytest.mark.asyncio
    async def test_update_user_empty(self):
        from src.db.users import update_user_db
        from src.models.user import UserUpdate
        with pytest.raises(EmptyUpdateError):
            await update_user_db(FID, UserUpdate(), _db(_col()))

    @pytest.mark.asyncio
    async def test_update_user_not_found(self):
        from src.db.users import update_user_db
        from src.models.user import UserUpdate
        with pytest.raises(UserNotFoundError):
            await update_user_db(FID, UserUpdate(display_name="X"), _db(_col(find_one=None)))

    @pytest.mark.asyncio
    async def test_delete_user(self):
        from src.db.users import delete_user_db
        assert await delete_user_db(FID, _db(_col())) is True

    @pytest.mark.asyncio
    async def test_delete_user_not_found(self):
        from src.db.users import delete_user_db
        with pytest.raises(UserNotFoundError):
            await delete_user_db(FID, _db(_col(deleted=0)))


# ═════════════════════════════════════════════════════════════════════════════
#  FACTS
# ═════════════════════════════════════════════════════════════════════════════
class TestFactsDB:
    @pytest.mark.asyncio
    async def test_get_all_facts(self):
        from src.db.facts import get_all_facts
        db = _db(_col(find_docs=[_fact_doc()]))
        assert len(await get_all_facts(db)) == 1

    @pytest.mark.asyncio
    async def test_get_all_facts_with_category(self):
        from src.db.facts import get_all_facts
        c = _col(find_docs=[_fact_doc()])
        db = _db(c)
        await get_all_facts(db, category="history", approved_only=False)
        c.find.assert_called_once_with({"category": "history"})

    @pytest.mark.asyncio
    async def test_get_random_fact(self):
        from src.db.facts import get_random_fact
        db = _db(_col(agg_docs=[_fact_doc()]))
        f = await get_random_fact(db)
        assert f is not None and f.content == "F1 fact content here for testing"

    @pytest.mark.asyncio
    async def test_get_random_fact_none(self):
        from src.db.facts import get_random_fact
        db = _db(_col(agg_docs=[]))
        assert await get_random_fact(db) is None

    @pytest.mark.asyncio
    async def test_get_fact_by_id(self):
        from src.db.facts import get_fact_by_id
        db = _db(_col(find_one=_fact_doc()))
        assert (await get_fact_by_id(FID, db)).content == "F1 fact content here for testing"

    @pytest.mark.asyncio
    async def test_get_fact_by_id_not_found(self):
        from src.db.facts import get_fact_by_id
        with pytest.raises(FactNotFoundError):
            await get_fact_by_id(FID, _db(_col(find_one=None)))

    @pytest.mark.asyncio
    async def test_create_fact(self):
        from src.db.facts import create_fact_db
        from src.models.fact import FactCreate
        c = _col(find_one=_fact_doc())
        db = _db(c)
        f = await create_fact_db(FID, FactCreate(content="A fun F1 fact for testing"), db)
        assert f.content == "F1 fact content here for testing"
        c.insert_one.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_approve_fact(self):
        from src.db.facts import approve_fact_db
        db = _db(_col(find_one=_fact_doc(approved=True)))
        f = await approve_fact_db(FID, db)
        assert f.approved is True

    @pytest.mark.asyncio
    async def test_approve_fact_not_found(self):
        from src.db.facts import approve_fact_db
        c = _col(find_one=None)
        c.update_one = AsyncMock(return_value=MagicMock(matched_count=0))
        with pytest.raises(FactNotFoundError):
            await approve_fact_db(FID, _db(c))

    @pytest.mark.asyncio
    async def test_like_fact_toggle_on(self):
        from src.db.facts import like_fact_db
        doc = _fact_doc(liked_by=[])
        c = _col(find_one=doc)
        db = _db(c)
        await like_fact_db(FID, "user123", db)
        # Should push user to liked_by
        assert c.update_one.await_count >= 1

    @pytest.mark.asyncio
    async def test_like_fact_toggle_off(self):
        from src.db.facts import like_fact_db
        doc = _fact_doc(liked_by=["user123"])
        c = _col(find_one=doc)
        db = _db(c)
        await like_fact_db(FID, "user123", db)
        # Should pull user from liked_by
        assert c.update_one.await_count >= 1

    @pytest.mark.asyncio
    async def test_like_fact_not_found(self):
        from src.db.facts import like_fact_db
        with pytest.raises(FactNotFoundError):
            await like_fact_db(FID, "user123", _db(_col(find_one=None)))

    @pytest.mark.asyncio
    async def test_delete_fact(self):
        from src.db.facts import delete_fact_db
        assert await delete_fact_db(FID, _db(_col())) is True

    @pytest.mark.asyncio
    async def test_delete_fact_not_found(self):
        from src.db.facts import delete_fact_db
        with pytest.raises(FactNotFoundError):
            await delete_fact_db(FID, _db(_col(deleted=0)))


# ═════════════════════════════════════════════════════════════════════════════
#  FAVOURITES
# ═════════════════════════════════════════════════════════════════════════════
class TestFavouritesDB:
    @pytest.mark.asyncio
    async def test_get_user_favourites(self):
        from src.db.favourites import get_user_favourites
        db = _db(_col(find_docs=[_fav_doc()]))
        result = await get_user_favourites(FID2, db)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_user_favourites_with_type(self):
        from src.db.favourites import get_user_favourites
        c = _col(find_docs=[_fav_doc()])
        db = _db(c)
        await get_user_favourites(FID2, db, list_type="drivers")
        call_args = c.find.call_args[0][0]
        assert call_args["list_type"] == "drivers"

    @pytest.mark.asyncio
    async def test_get_favourite_by_id(self):
        from src.db.favourites import get_favourite_by_id
        db = _db(_col(find_one=_fav_doc()))
        f = await get_favourite_by_id(FID, FID2, db)
        assert f.name == "My List"

    @pytest.mark.asyncio
    async def test_get_favourite_by_id_not_found(self):
        from src.db.favourites import get_favourite_by_id
        with pytest.raises(FavouriteListNotFoundError):
            await get_favourite_by_id(FID, FID2, _db(_col(find_one=None)))

    @pytest.mark.asyncio
    async def test_create_favourite(self):
        from src.db.favourites import create_favourite_db
        from src.models.favourite import FavouriteListCreate
        c = _col(find_one=_fav_doc())
        db = _db(c)
        f = await create_favourite_db(FID2, FavouriteListCreate(name="My List", list_type="drivers"), db)
        assert f.name == "My List"

    @pytest.mark.asyncio
    async def test_update_favourite(self):
        from src.db.favourites import update_favourite_db
        from src.models.favourite import FavouriteListUpdate
        db = _db(_col(find_one=_fav_doc()))
        f = await update_favourite_db(FID, FID2, FavouriteListUpdate(name="Renamed"), db)
        assert f.name == "My List"

    @pytest.mark.asyncio
    async def test_update_favourite_empty(self):
        from src.db.favourites import update_favourite_db
        from src.models.favourite import FavouriteListUpdate
        with pytest.raises(EmptyUpdateError):
            await update_favourite_db(FID, FID2, FavouriteListUpdate(), _db(_col()))

    @pytest.mark.asyncio
    async def test_update_favourite_not_found(self):
        from src.db.favourites import update_favourite_db
        from src.models.favourite import FavouriteListUpdate
        c = _col()
        c.update_one = AsyncMock(return_value=MagicMock(matched_count=0))
        with pytest.raises(FavouriteListNotFoundError):
            await update_favourite_db(FID, FID2, FavouriteListUpdate(name="X"), _db(c))

    @pytest.mark.asyncio
    async def test_delete_favourite(self):
        from src.db.favourites import delete_favourite_db
        assert await delete_favourite_db(FID, FID2, _db(_col())) is True

    @pytest.mark.asyncio
    async def test_delete_favourite_not_found(self):
        from src.db.favourites import delete_favourite_db
        with pytest.raises(FavouriteListNotFoundError):
            await delete_favourite_db(FID, FID2, _db(_col(deleted=0)))

    @pytest.mark.asyncio
    async def test_add_item(self):
        from src.db.favourites import add_item_to_favourite
        from src.models.favourite import AddFavouriteItem
        c = _col(find_one=_fav_doc())
        db = _db(c)
        f = await add_item_to_favourite(FID, FID2, AddFavouriteItem(item_id="x", name="Ham"), db)
        assert f.name == "My List"

    @pytest.mark.asyncio
    async def test_add_item_not_found(self):
        from src.db.favourites import add_item_to_favourite
        from src.models.favourite import AddFavouriteItem
        with pytest.raises(FavouriteListNotFoundError):
            await add_item_to_favourite(FID, FID2, AddFavouriteItem(item_id="x", name="Ham"), _db(_col(find_one=None)))

    @pytest.mark.asyncio
    async def test_add_item_duplicate(self):
        from src.db.favourites import add_item_to_favourite
        from src.models.favourite import AddFavouriteItem
        doc = _fav_doc(items=[{"item_id": "x", "name": "Ham"}])
        with pytest.raises(DuplicateFavouriteItemError):
            await add_item_to_favourite(FID, FID2, AddFavouriteItem(item_id="x", name="Ham"), _db(_col(find_one=doc)))

    @pytest.mark.asyncio
    async def test_remove_item(self):
        from src.db.favourites import remove_item_from_favourite
        c = _col(find_one=_fav_doc())
        db = _db(c)
        f = await remove_item_from_favourite(FID, FID2, "x", db)
        assert f.name == "My List"

    @pytest.mark.asyncio
    async def test_remove_item_not_found(self):
        from src.db.favourites import remove_item_from_favourite
        c = _col()
        c.update_one = AsyncMock(return_value=MagicMock(matched_count=0))
        with pytest.raises(FavouriteListNotFoundError):
            await remove_item_from_favourite(FID, FID2, "x", _db(c))


# ═════════════════════════════════════════════════════════════════════════════
#  HEAD TO HEAD
# ═════════════════════════════════════════════════════════════════════════════
class TestHeadToHeadDB:
    @pytest.mark.asyncio
    async def test_cast_new_vote(self):
        from src.db.head_to_head import cast_h2h_vote
        from src.models.head_to_head import HeadToHeadVoteCreate
        c = _col(find_one=None)
        # After insert, find_one returns the vote doc
        c.find_one = AsyncMock(side_effect=[None, _vote_doc()])
        db = _db(c)
        data = HeadToHeadVoteCreate(driver1_id=FID, driver2_id=FID2, winner_id=FID)
        v = await cast_h2h_vote(FID, data, db)
        assert v.winner_id == FID

    @pytest.mark.asyncio
    async def test_cast_vote_updates_existing(self):
        from src.db.head_to_head import cast_h2h_vote
        from src.models.head_to_head import HeadToHeadVoteCreate
        existing = _vote_doc()
        c = _col()
        c.find_one = AsyncMock(side_effect=[existing, _vote_doc(winner_id=FID2)])
        db = _db(c)
        data = HeadToHeadVoteCreate(driver1_id=FID, driver2_id=FID2, winner_id=FID2)
        v = await cast_h2h_vote(FID, data, db)
        c.update_one.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_cast_vote_invalid_winner(self):
        from src.db.head_to_head import cast_h2h_vote
        from src.models.head_to_head import HeadToHeadVoteCreate
        db = _db(_col())
        data = HeadToHeadVoteCreate(driver1_id=FID, driver2_id=FID2, winner_id="507f1f77bcf86cd799439099")
        with pytest.raises(InvalidVoteError):
            await cast_h2h_vote(FID, data, db)

    @pytest.mark.asyncio
    async def test_get_h2h_results(self):
        from src.db.head_to_head import get_h2h_results
        agg_docs = [{"_id": FID, "votes": 3}, {"_id": FID2, "votes": 2}]
        db = _db(_col(agg_docs=agg_docs))
        r = await get_h2h_results(FID, FID2, db)
        assert r["total_votes"] == 5


# ═════════════════════════════════════════════════════════════════════════════
#  HOT TAKES
# ═════════════════════════════════════════════════════════════════════════════
class TestHotTakesDB:
    @pytest.mark.asyncio
    async def test_get_all_hot_takes(self):
        from src.db.hot_takes import get_all_hot_takes
        db = _db(_col(find_docs=[_take_doc()]))
        result = await get_all_hot_takes(db)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_all_hot_takes_by_category(self):
        from src.db.hot_takes import get_all_hot_takes
        c = _col(find_docs=[_take_doc()])
        db = _db(c)
        await get_all_hot_takes(db, category="driver", sort_by="spicy")
        c.find.assert_called_once_with({"category": "driver"})

    @pytest.mark.asyncio
    async def test_get_hot_take_by_id(self):
        from src.db.hot_takes import get_hot_take_by_id
        db = _db(_col(find_one=_take_doc()))
        t = await get_hot_take_by_id(FID, db)
        assert "hot take" in t.content

    @pytest.mark.asyncio
    async def test_get_hot_take_not_found(self):
        from src.db.hot_takes import get_hot_take_by_id
        with pytest.raises(HotTakeNotFoundError):
            await get_hot_take_by_id(FID, _db(_col(find_one=None)))

    @pytest.mark.asyncio
    async def test_create_hot_take(self):
        from src.db.hot_takes import create_hot_take_db
        from src.models.hot_take import HotTakeCreate
        c = _col(find_one=_take_doc())
        db = _db(c)
        t = await create_hot_take_db(FID, "Tester", HotTakeCreate(content="Hot take content for testing"), db)
        assert "hot take" in t.content

    @pytest.mark.asyncio
    async def test_react_agree(self):
        from src.db.hot_takes import react_to_hot_take
        doc = _take_doc(agreed_by=[], disagreed_by=[])
        c = _col(find_one=doc)
        db = _db(c)
        await react_to_hot_take(FID, "user1", "agree", db)
        assert c.update_one.await_count >= 1

    @pytest.mark.asyncio
    async def test_react_disagree(self):
        from src.db.hot_takes import react_to_hot_take
        doc = _take_doc(agreed_by=[], disagreed_by=[])
        c = _col(find_one=doc)
        db = _db(c)
        await react_to_hot_take(FID, "user1", "disagree", db)
        assert c.update_one.await_count >= 1

    @pytest.mark.asyncio
    async def test_react_toggle_off_agree(self):
        from src.db.hot_takes import react_to_hot_take
        doc = _take_doc(agreed_by=["user1"], disagreed_by=[])
        c = _col(find_one=doc)
        db = _db(c)
        await react_to_hot_take(FID, "user1", "agree", db)
        # Toggle off: remove agree but don't add new
        assert c.update_one.await_count >= 1

    @pytest.mark.asyncio
    async def test_react_toggle_off_disagree(self):
        from src.db.hot_takes import react_to_hot_take
        doc = _take_doc(agreed_by=[], disagreed_by=["user1"])
        c = _col(find_one=doc)
        db = _db(c)
        await react_to_hot_take(FID, "user1", "disagree", db)
        assert c.update_one.await_count >= 1

    @pytest.mark.asyncio
    async def test_react_not_found(self):
        from src.db.hot_takes import react_to_hot_take
        with pytest.raises(HotTakeNotFoundError):
            await react_to_hot_take(FID, "user1", "agree", _db(_col(find_one=None)))

    @pytest.mark.asyncio
    async def test_delete_hot_take(self):
        from src.db.hot_takes import delete_hot_take_db
        assert await delete_hot_take_db(FID, FID, _db(_col())) is True

    @pytest.mark.asyncio
    async def test_delete_hot_take_as_admin(self):
        from src.db.hot_takes import delete_hot_take_db
        assert await delete_hot_take_db(FID, FID, _db(_col()), is_admin=True) is True

    @pytest.mark.asyncio
    async def test_delete_hot_take_not_found(self):
        from src.db.hot_takes import delete_hot_take_db
        with pytest.raises(HotTakeDeleteNotFoundError):
            await delete_hot_take_db(FID, FID, _db(_col(deleted=0)))


# ═════════════════════════════════════════════════════════════════════════════
#  PREDICTIONS
# ═════════════════════════════════════════════════════════════════════════════
class TestPredictionsDB:
    @pytest.mark.asyncio
    async def test_get_user_predictions(self):
        from src.db.predictions import get_user_predictions
        db = _db(_col(find_docs=[_pred_doc()]))
        result = await get_user_predictions(FID, db)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_user_predictions_filtered(self):
        from src.db.predictions import get_user_predictions
        c = _col(find_docs=[_pred_doc()])
        db = _db(c)
        await get_user_predictions(FID, db, season=2025, category="driver_championship")
        call_args = c.find.call_args[0][0]
        assert call_args["season"] == 2025
        assert call_args["category"] == "driver_championship"

    @pytest.mark.asyncio
    async def test_get_prediction_by_id(self):
        from src.db.predictions import get_prediction_by_id
        db = _db(_col(find_one=_pred_doc()))
        p = await get_prediction_by_id(FID, db)
        assert p.predicted_name == "Max Verstappen"

    @pytest.mark.asyncio
    async def test_get_prediction_by_id_not_found(self):
        from src.db.predictions import get_prediction_by_id
        with pytest.raises(PredictionNotFoundError):
            await get_prediction_by_id(FID, _db(_col(find_one=None)))

    @pytest.mark.asyncio
    async def test_create_prediction(self):
        from src.db.predictions import create_prediction_db
        from src.models.prediction import PredictionCreate
        c = _col(find_one=None)
        # find_one returns None (no dup), then returns new doc after insert
        c.find_one = AsyncMock(side_effect=[None, _pred_doc()])
        db = _db(c)
        p = await create_prediction_db(
            FID,
            PredictionCreate(
                season=2025, category="driver_championship",
                predicted_id=FID2, predicted_name="Max Verstappen",
            ),
            db,
        )
        assert p.predicted_name == "Max Verstappen"

    @pytest.mark.asyncio
    async def test_create_prediction_duplicate(self):
        from src.db.predictions import create_prediction_db
        from src.models.prediction import PredictionCreate
        c = _col(find_one=_pred_doc())
        db = _db(c)
        with pytest.raises(DuplicatePredictionError):
            await create_prediction_db(
                FID,
                PredictionCreate(
                    season=2025, category="driver_championship",
                    predicted_id=FID2, predicted_name="Max Verstappen",
                ),
                db,
            )

    @pytest.mark.asyncio
    async def test_update_prediction(self):
        from src.db.predictions import update_prediction_db
        from src.models.prediction import PredictionUpdate
        db = _db(_col(find_one=_pred_doc()))
        p = await update_prediction_db(FID, FID, PredictionUpdate(confidence=9), db)
        assert p.predicted_name == "Max Verstappen"

    @pytest.mark.asyncio
    async def test_update_prediction_empty(self):
        from src.db.predictions import update_prediction_db
        from src.models.prediction import PredictionUpdate
        with pytest.raises(EmptyUpdateError):
            await update_prediction_db(FID, FID, PredictionUpdate(), _db(_col()))

    @pytest.mark.asyncio
    async def test_update_prediction_not_found(self):
        from src.db.predictions import update_prediction_db
        from src.models.prediction import PredictionUpdate
        c = _col()
        c.update_one = AsyncMock(return_value=MagicMock(matched_count=0))
        with pytest.raises(PredictionNotFoundError):
            await update_prediction_db(FID, FID, PredictionUpdate(confidence=9), _db(c))

    @pytest.mark.asyncio
    async def test_delete_prediction(self):
        from src.db.predictions import delete_prediction_db
        assert await delete_prediction_db(FID, FID, _db(_col())) is True

    @pytest.mark.asyncio
    async def test_delete_prediction_not_found(self):
        from src.db.predictions import delete_prediction_db
        with pytest.raises(PredictionNotFoundError):
            await delete_prediction_db(FID, FID, _db(_col(deleted=0)))

    @pytest.mark.asyncio
    async def test_leaderboard(self):
        from src.db.predictions import get_prediction_leaderboard
        agg_docs = [
            {"_id": {"predicted_id": FID, "predicted_name": "Max"}, "vote_count": 5, "avg_confidence": 8.2},
        ]
        db = _db(_col(agg_docs=agg_docs))
        result = await get_prediction_leaderboard(db, 2025, "driver_championship")
        assert len(result) == 1
        assert result[0].vote_count == 5
