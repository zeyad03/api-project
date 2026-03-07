"""Tests for /predictions endpoints."""

from unittest.mock import AsyncMock, patch

from src.core.exceptions import (
    DuplicatePredictionError,
    PredictionNotFoundError,
)
from src.models.prediction import Prediction, LeaderboardEntry

from .conftest import FAKE_PRED_ID, FAKE_DRIVER_ID, FAKE_USER_ID, TIMESTAMP


def _prediction(**overrides):
    defaults = dict(
        id=FAKE_PRED_ID, user_id=FAKE_USER_ID, season=2025,
        category="driver_championship", predicted_id=FAKE_DRIVER_ID,
        predicted_name="Lewis Hamilton", confidence=8,
        reasoning="Goat", created_at=TIMESTAMP,
    )
    defaults.update(overrides)
    return Prediction(**defaults)


# ── List my predictions ──────────────────────────────────────────────────────
class TestListPredictions:
    @patch("src.routers.predictions.get_user_predictions", new_callable=AsyncMock)
    def test_list_all(self, mock_get, auth_client):
        mock_get.return_value = [_prediction()]
        resp = auth_client.get("/predictions")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    @patch("src.routers.predictions.get_user_predictions", new_callable=AsyncMock)
    def test_filter_by_season(self, mock_get, auth_client):
        mock_get.return_value = [_prediction()]
        resp = auth_client.get("/predictions?season=2025")
        assert resp.status_code == 200

    @patch("src.routers.predictions.get_user_predictions", new_callable=AsyncMock)
    def test_filter_by_category(self, mock_get, auth_client):
        mock_get.return_value = []
        resp = auth_client.get("/predictions?category=driver_championship")
        assert resp.status_code == 200

    def test_unauthenticated(self, client):
        resp = client.get("/predictions")
        assert resp.status_code == 401


# ── Get single prediction ───────────────────────────────────────────────────
class TestGetPrediction:
    @patch("src.routers.predictions.get_prediction_by_id", new_callable=AsyncMock)
    def test_found(self, mock_get, auth_client):
        mock_get.return_value = _prediction()
        resp = auth_client.get(f"/predictions/view/{FAKE_PRED_ID}")
        assert resp.status_code == 200
        assert resp.json()["predicted_name"] == "Lewis Hamilton"

    @patch("src.routers.predictions.get_prediction_by_id", new_callable=AsyncMock)
    def test_not_found(self, mock_get, auth_client):
        mock_get.side_effect = PredictionNotFoundError(FAKE_PRED_ID)
        resp = auth_client.get(f"/predictions/view/{FAKE_PRED_ID}")
        assert resp.status_code == 404


# ── Create prediction ────────────────────────────────────────────────────────
class TestCreatePrediction:
    @patch("src.routers.predictions.create_prediction_db", new_callable=AsyncMock)
    def test_success(self, mock_create, auth_client):
        mock_create.return_value = _prediction()
        resp = auth_client.post("/predictions", json={
            "season": 2025, "category": "driver_championship",
            "predicted_id": FAKE_DRIVER_ID, "predicted_name": "Lewis Hamilton",
            "confidence": 8, "reasoning": "Goat",
        })
        assert resp.status_code == 201
        assert resp.json()["predicted_name"] == "Lewis Hamilton"

    @patch("src.routers.predictions.create_prediction_db", new_callable=AsyncMock)
    def test_duplicate_conflict(self, mock_create, auth_client):
        mock_create.side_effect = DuplicatePredictionError("driver_championship", 2025)
        resp = auth_client.post("/predictions", json={
            "season": 2025, "category": "driver_championship",
            "predicted_id": FAKE_DRIVER_ID, "predicted_name": "Lewis Hamilton",
        })
        assert resp.status_code == 409

    def test_invalid_category(self, auth_client):
        resp = auth_client.post("/predictions", json={
            "season": 2025, "category": "invalid",
            "predicted_id": FAKE_DRIVER_ID, "predicted_name": "X",
        })
        assert resp.status_code == 422

    def test_confidence_out_of_range(self, auth_client):
        resp = auth_client.post("/predictions", json={
            "season": 2025, "category": "driver_championship",
            "predicted_id": FAKE_DRIVER_ID, "predicted_name": "X",
            "confidence": 11,
        })
        assert resp.status_code == 422


# ── Update prediction ────────────────────────────────────────────────────────
class TestUpdatePrediction:
    @patch("src.routers.predictions.update_prediction_db", new_callable=AsyncMock)
    def test_success(self, mock_update, auth_client):
        mock_update.return_value = _prediction(confidence=10)
        resp = auth_client.patch(f"/predictions/{FAKE_PRED_ID}", json={"confidence": 10})
        assert resp.status_code == 200
        assert resp.json()["confidence"] == 10

    @patch("src.routers.predictions.update_prediction_db", new_callable=AsyncMock)
    def test_not_found(self, mock_update, auth_client):
        mock_update.side_effect = PredictionNotFoundError(FAKE_PRED_ID)
        resp = auth_client.patch(f"/predictions/{FAKE_PRED_ID}", json={"confidence": 5})
        assert resp.status_code == 404


# ── Delete prediction ────────────────────────────────────────────────────────
class TestDeletePrediction:
    @patch("src.routers.predictions.delete_prediction_db", new_callable=AsyncMock, return_value=True)
    def test_success(self, _del, auth_client):
        resp = auth_client.delete(f"/predictions/{FAKE_PRED_ID}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    @patch("src.routers.predictions.delete_prediction_db", new_callable=AsyncMock)
    def test_not_found(self, mock_del, auth_client):
        mock_del.side_effect = PredictionNotFoundError(FAKE_PRED_ID)
        resp = auth_client.delete(f"/predictions/{FAKE_PRED_ID}")
        assert resp.status_code == 404


# ── Leaderboards (public) ───────────────────────────────────────────────────
class TestLeaderboard:
    @patch("src.routers.predictions.get_prediction_leaderboard", new_callable=AsyncMock)
    def test_driver_leaderboard(self, mock_lb, client):
        mock_lb.return_value = [
            LeaderboardEntry(
                predicted_id=FAKE_DRIVER_ID, predicted_name="Lewis Hamilton",
                vote_count=10, avg_confidence=7.5,
            )
        ]
        resp = client.get("/predictions/leaderboard/drivers?season=2025")
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["predicted_name"] == "Lewis Hamilton"

    @patch("src.routers.predictions.get_prediction_leaderboard", new_callable=AsyncMock)
    def test_constructor_leaderboard(self, mock_lb, client):
        mock_lb.return_value = []
        resp = client.get("/predictions/leaderboard/constructors?season=2025")
        assert resp.status_code == 200
        assert resp.json() == []
