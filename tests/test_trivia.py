"""Tests for /trivia endpoints – facts CRUD & quiz."""

from unittest.mock import AsyncMock, patch

from src.models.fact import Fact

from .conftest import FAKE_FACT_ID, FAKE_USER_ID, TIMESTAMP


def _fact(**overrides):
    defaults = dict(
        id=FAKE_FACT_ID, content="Monza is the Temple of Speed.",
        category="fun", source="", submitted_by=FAKE_USER_ID,
        approved=True, likes=0, liked_by=[], created_at=TIMESTAMP,
    )
    defaults.update(overrides)
    return Fact(**defaults)


# ── Random fact ──────────────────────────────────────────────────────────────
class TestRandomFact:
    @patch("src.routers.trivia.get_random_fact", new_callable=AsyncMock)
    def test_returns_fact(self, mock_get, client):
        mock_get.return_value = _fact()
        resp = client.get("/trivia/random")
        assert resp.status_code == 200
        assert "Monza" in resp.json()["content"]

    @patch("src.routers.trivia.get_random_fact", new_callable=AsyncMock, return_value=None)
    def test_no_facts_available(self, _m, client):
        resp = client.get("/trivia/random")
        assert resp.status_code == 200
        assert "message" in resp.json()

    @patch("src.routers.trivia.get_random_fact", new_callable=AsyncMock)
    def test_filter_by_category(self, mock_get, client):
        mock_get.return_value = _fact(category="history")
        resp = client.get("/trivia/random?category=history")
        assert resp.status_code == 200


# ── List facts ───────────────────────────────────────────────────────────────
class TestListFacts:
    @patch("src.routers.trivia.get_all_facts", new_callable=AsyncMock)
    def test_list_all(self, mock_get, client):
        mock_get.return_value = [_fact()]
        resp = client.get("/trivia")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    @patch("src.routers.trivia.get_all_facts", new_callable=AsyncMock, return_value=[])
    def test_list_empty(self, _m, client):
        resp = client.get("/trivia")
        assert resp.status_code == 200
        assert resp.json() == []


# ── Submit a fact ────────────────────────────────────────────────────────────
class TestSubmitFact:
    @patch("src.routers.trivia.create_fact_db", new_callable=AsyncMock)
    def test_submit(self, mock_create, auth_client):
        mock_create.return_value = _fact(approved=False)
        resp = auth_client.post("/trivia", json={
            "content": "Monza is the Temple of Speed.", "category": "fun",
        })
        assert resp.status_code == 201

    def test_unauthenticated(self, client):
        resp = client.post("/trivia", json={
            "content": "Some fact here that is long enough.", "category": "fun",
        })
        assert resp.status_code == 401

    def test_invalid_category(self, auth_client):
        resp = auth_client.post("/trivia", json={
            "content": "A valid long enough fact.", "category": "invalid",
        })
        assert resp.status_code == 422


# ── Like / unlike ────────────────────────────────────────────────────────────
class TestLikeFact:
    @patch("src.routers.trivia.like_fact_db", new_callable=AsyncMock)
    def test_toggle_like(self, mock_like, auth_client):
        mock_like.return_value = _fact(likes=1, liked_by=[FAKE_USER_ID])
        resp = auth_client.post(f"/trivia/{FAKE_FACT_ID}/like")
        assert resp.status_code == 200
        assert resp.json()["likes"] == 1


# ── Approve fact (admin) ─────────────────────────────────────────────────────
class TestApproveFact:
    @patch("src.routers.trivia.approve_fact_db", new_callable=AsyncMock)
    def test_admin_approve(self, mock_approve, admin_client):
        mock_approve.return_value = _fact(approved=True)
        resp = admin_client.patch(f"/trivia/{FAKE_FACT_ID}/approve")
        assert resp.status_code == 200
        assert resp.json()["approved"] is True

    def test_regular_user_forbidden(self, auth_client):
        resp = auth_client.patch(f"/trivia/{FAKE_FACT_ID}/approve")
        assert resp.status_code == 403


# ── Delete fact (admin) ──────────────────────────────────────────────────────
class TestDeleteFact:
    @patch("src.routers.trivia.delete_fact_db", new_callable=AsyncMock, return_value=True)
    def test_admin_delete(self, _del, admin_client):
        resp = admin_client.delete(f"/trivia/{FAKE_FACT_ID}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_regular_user_forbidden(self, auth_client):
        resp = auth_client.delete(f"/trivia/{FAKE_FACT_ID}")
        assert resp.status_code == 403


# ── Quiz ─────────────────────────────────────────────────────────────────────
class TestQuiz:
    def test_get_question(self, client):
        resp = client.get("/trivia/quiz")
        assert resp.status_code == 200
        body = resp.json()
        assert "question" in body
        assert "options" in body
        assert len(body["options"]) == 4

    def test_answer_correct(self, client):
        resp = client.post("/trivia/quiz/answer", json={
            "question_id": "q01", "answer": "Monza",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["correct"] is True
        assert body["correct_answer"] == "Monza"

    def test_answer_incorrect(self, client):
        resp = client.post("/trivia/quiz/answer", json={
            "question_id": "q01", "answer": "Silverstone",
        })
        assert resp.status_code == 200
        assert resp.json()["correct"] is False

    def test_answer_unknown_question(self, client):
        resp = client.post("/trivia/quiz/answer", json={
            "question_id": "q99", "answer": "X",
        })
        assert resp.status_code == 200
        assert resp.json()["correct"] is False
