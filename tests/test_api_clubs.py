"""
Tests for clubs and availability API endpoints.
"""
import pytest
from datetime import datetime, timedelta


class TestClubsAPI:
    """Test /api/clubs endpoint."""

    async def test_get_clubs_empty(self, client):
        response = await client.get("/api/clubs")
        assert response.status_code == 200
        data = response.json()
        assert data["clubs"] == []
        assert data["total"] == 0
        assert data["page"] == 1

    async def test_get_clubs_with_data(self, client, db_session):
        from models import Club
        club = Club(name="Test Club", city="Tashkent", address="Test St 1",
                    driver_type="MOCK", is_active=True)
        db_session.add(club)
        await db_session.commit()

        response = await client.get("/api/clubs")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["clubs"][0]["name"] == "Test Club"

    async def test_get_clubs_pagination(self, client, db_session):
        from models import Club
        for i in range(15):
            db_session.add(Club(name=f"Club {i}", city="Tashkent",
                               address=f"St {i}", driver_type="MOCK", is_active=True))
        await db_session.commit()

        # Page 1 (10 items)
        r1 = await client.get("/api/clubs?page=1&limit=10")
        assert r1.status_code == 200
        assert len(r1.json()["clubs"]) == 10

        # Page 2 (5 items)
        r2 = await client.get("/api/clubs?page=2&limit=10")
        assert r2.status_code == 200
        assert len(r2.json()["clubs"]) == 5

    async def test_get_clubs_inactive_filter(self, client, db_session):
        from models import Club
        db_session.add(Club(name="Active", city="T", address="A", driver_type="MOCK", is_active=True))
        db_session.add(Club(name="Inactive", city="T", address="B", driver_type="MOCK", is_active=False))
        await db_session.commit()

        r = await client.get("/api/clubs?is_active=true")
        assert len(r.json()["clubs"]) == 1
        assert r.json()["clubs"][0]["name"] == "Active"


class TestComputersAPI:
    """Test /api/clubs/{id}/computers endpoint."""

    async def test_get_computers_club_not_found(self, client):
        r = await client.get("/api/clubs/999/computers")
        assert r.status_code == 404

    async def test_get_computers_returns_list(self, client, db_session):
        from models import Club, Computer
        club = Club(name="PC Club", city="Tashkent", address="Test",
                    driver_type="MOCK", is_active=True)
        db_session.add(club)
        await db_session.flush()

        for i in range(3):
            db_session.add(Computer(club_id=club.id, name=f"PC-{i}",
                                    zone="VIP", price_per_hour=15000, is_active=True))
        await db_session.commit()

        r = await client.get(f"/api/clubs/{club.id}/computers")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3


class TestAvailabilityAPI:
    """Test /api/availability endpoint."""

    async def test_availability_invalid_date(self, client):
        r = await client.get("/api/availability?club_id=1&computer_id=1&date=bad-date")
        assert r.status_code == 400

    async def test_availability_club_not_found(self, client):
        r = await client.get("/api/availability?club_id=999&computer_id=1&date=2030-01-01")
        assert r.status_code == 404

    async def test_availability_returns_occupied_hours(self, client, db_session):
        from models import Club, Computer
        club = Club(name="Avail Club", city="T", address="A",
                    driver_type="MOCK", is_active=True)
        db_session.add(club)
        await db_session.flush()

        pc = Computer(club_id=club.id, name="PC-1", zone="STD",
                      price_per_hour=10000, is_active=True)
        db_session.add(pc)
        await db_session.commit()

        future = (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d")
        r = await client.get(f"/api/availability?club_id={club.id}&computer_id={pc.id}&date={future}")
        assert r.status_code == 200
        assert "occupied_hours" in r.json()
