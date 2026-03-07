"""Tests for /calendar endpoints."""


class TestGetCalendar:
    def test_full_calendar(self, client):
        resp = client.get("/calendar")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 24
        assert data[0]["round"] == 1
        assert data[0]["name"] == "Australian Grand Prix"

    def test_upcoming_only(self, client):
        resp = client.get("/calendar?upcoming_only=true")
        assert resp.status_code == 200
        data = resp.json()
        # All returned races should have a date >= today
        if data:
            from datetime import date
            today = date.today().isoformat()
            assert all(r["date"] >= today for r in data)


class TestGetRace:
    def test_valid_round(self, client):
        resp = client.get("/calendar/1")
        assert resp.status_code == 200
        body = resp.json()
        assert body["round"] == 1
        assert body["name"] == "Australian Grand Prix"
        assert body["circuit"] == "Albert Park"

    def test_last_round(self, client):
        resp = client.get("/calendar/24")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Abu Dhabi Grand Prix"

    def test_invalid_round(self, client):
        resp = client.get("/calendar/99")
        assert resp.status_code == 404

    def test_round_zero(self, client):
        resp = client.get("/calendar/0")
        assert resp.status_code == 404
