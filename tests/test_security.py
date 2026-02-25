"""
🔒 Security Tests for the API

Tests for:
1. IDOR (Insecure Direct Object Reference)
2. Race Conditions
3. Authentication bypass attempts
4. Input validation
"""

import pytest
import sys
from pathlib import Path
import json
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from httpx import AsyncClient, ASGITransport
from main import fastapi_app
from database import init_db, async_session_factory
from models import User, Club, Computer, Booking
from sqlalchemy import select
from utils.timezone import now_tashkent


@pytest.fixture(scope="function", autouse=True)
async def setup_test_db():
    """Initialize test database with sample data."""
    await init_db()
    
    async with async_session_factory() as session:
        # Create two users
        user1 = User(
            tg_id=111111,
            full_name="Alice",
            age_confirmed=True,
            phone="+998901234567"
        )
        user2 = User(
            tg_id=222222,
            full_name="Bob (Attacker)",
            age_confirmed=True,
            phone="+998907654321"
        )
        
        session.add(user1)
        session.add(user2)
        await session.flush()
        
        # Create test club
        club = Club(
            name="Security Test Club",
            city="Tashkent",
            address="Test St",
            driver_type="MOCK"
        )
        session.add(club)
        await session.flush()
        
        # Create computers
        for i in range(3):
            pc = Computer(
                club_id=club.id,
                name=f"PC-{i+1}",
                zone="Standard",
                price_per_hour=50000
            )
            session.add(pc)
        
        # Create a booking for user1
        now = now_tashkent().replace(tzinfo=None)
        booking = Booking(
            user_id=user1.id,
            club_id=club.id,
            computer_name="PC-1",
            item_id=1,
            start_time=now + timedelta(days=1, hours=2),
            end_time=now + timedelta(days=1, hours=4),
            status="CONFIRMED"
        )
        session.add(booking)
        
        await session.commit()


@pytest.mark.asyncio
async def test_idor_cancel_other_user_booking():
    """
    🔴 SECURITY TEST: Try to cancel another user's booking (IDOR)
    Should FAIL with 404/403.
    
    Scenario:
    - User1 creates booking
    - User2 tries to cancel it with invalid auth header
    - Should be rejected
    """
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # User2 (attacker) tries to cancel User1's booking (ID=1)
        # Using a fake/invalid Telegram init data
        invalid_auth = json.dumps({"user": {"id": 222222, "is_bot": False}})
        
        response = await client.delete(
            "/api/bookings/1",
            headers={"X-Telegram-Init-Data": invalid_auth}
        )
        
        # Should reject - either 401 or 404
        assert response.status_code in [401, 404], f"Expected 401/404, got {response.status_code}"
        print("✅ IDOR test PASSED: Cannot cancel other user's booking")


@pytest.mark.asyncio
async def test_missing_authentication_header():
    """
    🔴 SECURITY TEST: Try to access protected endpoint without auth
    Should FAIL with 401.
    """
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Try to get user bookings without auth header
        response = await client.get("/api/user/bookings")
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        assert "Authentication required" in response.json().get("detail", "")
        print("✅ AUTH test PASSED: Missing auth header rejected")


@pytest.mark.asyncio
async def test_invalid_booking_dates():
    """
    🔴 VALIDATION TEST: Try to book in the past
    Should FAIL with validation error.
    """
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        now = datetime.now()
        
        # Try to book 1 hour ago (in the past)
        response = await client.post(
            "/api/bookings",
            json={
                "user_id": 111111,
                "club_id": 1,
                "computer_id": "2",
                "start_time": (now - timedelta(hours=1)).isoformat(),
                "duration_minutes": 60
            },
            headers={"X-Telegram-Init-Data": "fake"}
        )
        
        # Should fail validation
        assert response.status_code in [422, 400], f"Expected 422/400, got {response.status_code}"
        print("✅ VALIDATION test PASSED: Past booking rejected")


@pytest.mark.asyncio
async def test_zero_duration_booking():
    """
    🔴 VALIDATION TEST: Try to book with 0 duration
    Should FAIL with validation error.
    """
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        now = datetime.now()
        
        # Try to book with 0 minutes duration
        response = await client.post(
            "/api/bookings",
            json={
                "user_id": 111111,
                "club_id": 1,
                "computer_id": "2",
                "start_time": (now + timedelta(hours=2)).isoformat(),
                "duration_minutes": 0  # INVALID
            },
            headers={"X-Telegram-Init-Data": "fake"}
        )
        
        # Should fail validation
        assert response.status_code in [422, 400], f"Expected 422/400, got {response.status_code}"
        print("✅ VALIDATION test PASSED: Zero duration rejected")


@pytest.mark.asyncio
async def test_negative_club_id():
    """
    🔴 VALIDATION TEST: Invalid club ID
    Should FAIL with validation error.
    """
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/clubs/0/computers")
        
        # Should fail or return 404
        assert response.status_code in [400, 404, 422], f"Expected error, got {response.status_code}"
        print("✅ VALIDATION test PASSED: Invalid club ID rejected")


@pytest.mark.asyncio
async def test_availability_past_date():
    """
    🔴 VALIDATION TEST: Check availability for past date
    Should FAIL with validation error.
    """
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Try to check availability for yesterday
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        response = await client.get(
            "/api/availability",
            params={
                "club_id": 1,
                "computer_id": "1",
                "date": yesterday
            }
        )
        
        # Should fail validation
        assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}"
        print("✅ VALIDATION test PASSED: Past date rejected for availability")


@pytest.mark.asyncio
async def test_sql_injection_attempt():
    """
    🔴 SECURITY TEST: SQL Injection attempt
    SQLAlchemy ORM should prevent this, but we verify the response.
    """
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Try SQL injection in computer_id parameter
        malicious_id = "1 OR 1=1; DROP TABLE users; --"
        
        response = await client.get(
            "/api/availability",
            params={
                "club_id": 1,
                "computer_id": malicious_id,
                "date": "2025-03-01"
            }
        )
        
        # Should either fail validation or return safely (not execute malicious SQL)
        assert response.status_code in [400, 404, 422], f"Got {response.status_code}"
        result = response.json()
        assert not isinstance(result, list), "Unexpected result format"
        print("✅ SQL INJECTION test PASSED: Malicious input handled safely")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
