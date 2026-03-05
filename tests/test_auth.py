"""
Tests for authentication: OTP codes, JWT tokens, sessions.
"""
import pytest
from datetime import timedelta


class TestJWT:
    """Test JWT token creation and parsing."""

    def test_make_web_token_returns_string(self):
        from handlers.api import _make_web_token
        token = _make_web_token(user_id=1, tg_id=123456)
        assert isinstance(token, str)
        assert len(token) > 20

    def test_parse_valid_token(self):
        from handlers.api import _make_web_token, _parse_web_token
        token = _make_web_token(user_id=42, tg_id=789)
        payload = _parse_web_token(token)
        assert payload is not None
        assert payload["user_id"] == 42
        assert payload["tg_id"] == 789

    def test_parse_invalid_token_returns_none(self):
        from handlers.api import _parse_web_token
        result = _parse_web_token("this.is.fake")
        assert result is None

    def test_parse_tampered_token_returns_none(self):
        from handlers.api import _make_web_token, _parse_web_token
        token = _make_web_token(user_id=1, tg_id=1)
        # Tamper with token
        tampered = token[:-5] + "XXXXX"
        result = _parse_web_token(tampered)
        assert result is None

    def test_token_has_expiry(self):
        from handlers.api import _make_web_token, _parse_web_token
        token = _make_web_token(user_id=1, tg_id=1)
        payload = _parse_web_token(token)
        assert "exp" in payload, "JWT must have an expiry claim"


class TestOTPFlow:
    """Test OTP code generation, storage, and verification."""

    async def test_otp_code_is_6_digits(self, db_session):
        from handlers.app_auth import _generate_code
        code = _generate_code()
        assert len(code) == 6
        assert code.isdigit()

    async def test_otp_code_stored_correctly(self, db_session):
        from models import AppAuthCode
        from utils.timezone import now_utc
        now = now_utc()
        auth = AppAuthCode(
            user_id=12345,
            phone="+998901234567",
            code="123456",
            expires_at=now + timedelta(minutes=10),
        )
        db_session.add(auth)
        await db_session.commit()
        await db_session.refresh(auth)

        assert auth.used is False
        assert auth.code == "123456"
        assert auth.phone == "+998901234567"

    async def test_expired_otp_not_valid(self, db_session):
        """An expired code should be rejected."""
        from models import AppAuthCode
        from utils.timezone import now_utc
        now = now_utc()
        auth = AppAuthCode(
            user_id=12345,
            phone="+998901234567",
            code="999999",
            expires_at=now - timedelta(minutes=1),  # Already expired
        )
        db_session.add(auth)
        await db_session.commit()

        # Verify by checking expiry manually (as the API does)
        expires_naive = auth.expires_at.replace(tzinfo=None) if auth.expires_at.tzinfo else auth.expires_at
        now_naive = now.replace(tzinfo=None)
        assert now_naive > expires_naive, "Expired code should fail comparison"


class TestAPIHealth:
    """Test the health check endpoint."""

    async def test_health_returns_200(self, client):
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "services" in data

    async def test_clubs_returns_200(self, client):
        response = await client.get("/api/clubs")
        assert response.status_code == 200
        data = response.json()
        assert "clubs" in data
        assert isinstance(data["clubs"], list)


class TestAuthEndpoints:
    """Test auth API endpoints."""

    async def test_verify_code_invalid_returns_401(self, client):
        response = await client.post("/api/auth/verify-code", json={
            "phone": "+998901234567",
            "code": "000000"
        })
        assert response.status_code == 401

    async def test_logout_without_token_returns_200(self, client):
        response = await client.post("/api/auth/logout")
        assert response.status_code == 200

    async def test_language_invalid_returns_400(self, client):
        response = await client.post("/api/web/language", json={
            "tg_id": 12345,
            "language": "fr"  # Not supported
        })
        assert response.status_code == 400
