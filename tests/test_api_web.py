"""
Tests for web auth and web profile API endpoints.
"""
import pytest
from datetime import timedelta


class TestWebLogin:
    """Test /api/web/login endpoint."""

    async def test_login_unknown_phone_returns_404(self, client):
        r = await client.post("/api/web/login", json={"phone": "+998991111111"})
        assert r.status_code == 404

    async def test_login_valid_user(self, client, db_session):
        from models import User
        user = User(tg_id=800, full_name="Web User", phone="+998901234567")
        db_session.add(user)
        await db_session.commit()

        r = await client.post("/api/web/login", json={"phone": "+998901234567"})
        assert r.status_code == 200
        data = r.json()
        assert "token" in data
        assert data["user"]["name"] == "Web User"

    async def test_login_normalizes_phone(self, client, db_session):
        from models import User
        user = User(tg_id=801, full_name="Normalizer", phone="+998901112233")
        db_session.add(user)
        await db_session.commit()

        # Send without +
        r = await client.post("/api/web/login", json={"phone": "998901112233"})
        assert r.status_code == 200


class TestWebProfile:
    """Test web profile endpoints."""

    async def _login(self, client, db_session):
        """Helper: create user, login, return token."""
        from models import User
        user = User(tg_id=900, full_name="Profile User", phone="+998909999999")
        db_session.add(user)
        await db_session.commit()

        r = await client.post("/api/web/login", json={"phone": "+998909999999"})
        return r.json()["token"]

    async def test_me_without_token_returns_401(self, client):
        r = await client.get("/api/web/me")
        assert r.status_code == 401

    async def test_me_with_token(self, client, db_session):
        token = await self._login(client, db_session)
        r = await client.get("/api/web/me",
                             headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert r.json()["name"] == "Profile User"

    async def test_profile_with_token(self, client, db_session):
        token = await self._login(client, db_session)
        r = await client.get("/api/web/profile",
                             headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert r.json()["full_name"] == "Profile User"

    async def test_profile_invalid_token(self, client):
        r = await client.get("/api/web/profile",
                             headers={"Authorization": "Bearer invalid.token.here"})
        assert r.status_code == 401


class TestWebLanguage:
    """Test language update endpoint."""

    async def test_set_language_valid(self, client, db_session):
        from models import User
        user = User(tg_id=850, full_name="Lang User")
        db_session.add(user)
        await db_session.commit()

        r = await client.post("/api/web/language",
                              json={"tg_id": 850, "language": "en"})
        assert r.status_code == 200
        assert r.json()["language"] == "en"

    async def test_set_language_uzbek(self, client, db_session):
        from models import User
        user = User(tg_id=851, full_name="Uz User")
        db_session.add(user)
        await db_session.commit()

        r = await client.post("/api/web/language",
                              json={"tg_id": 851, "language": "uz"})
        assert r.status_code == 200

    async def test_set_language_invalid(self, client, db_session):
        r = await client.post("/api/web/language",
                              json={"tg_id": 999, "language": "fr"})
        assert r.status_code == 400

    async def test_set_language_user_not_found(self, client, db_session):
        r = await client.post("/api/web/language",
                              json={"tg_id": 99999999, "language": "ru"})
        assert r.status_code == 404


class TestWebBookings:
    """Test web bookings endpoint."""

    async def test_web_bookings_without_auth(self, client):
        r = await client.get("/api/web/bookings")
        assert r.status_code == 401

    async def test_web_bookings_empty(self, client, db_session):
        from models import User
        user = User(tg_id=860, full_name="No Bookings", phone="+998908888888")
        db_session.add(user)
        await db_session.commit()

        login = await client.post("/api/web/login", json={"phone": "+998908888888"})
        token = login.json()["token"]

        r = await client.get("/api/web/bookings",
                             headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert r.json() == []
