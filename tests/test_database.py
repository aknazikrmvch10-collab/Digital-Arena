"""
Tests for database initialization and migration system.
"""
import pytest


class TestDatabaseInit:
    """Test database initialization."""

    async def test_init_db_creates_tables(self, db_session):
        """Tables should exist after init (conftest already calls create_all)."""
        from sqlalchemy import text
        result = await db_session.execute(
            text("SELECT name FROM sqlite_master WHERE type='table'")
        )
        tables = [row[0] for row in result.fetchall()]
        assert "users" in tables
        assert "clubs" in tables
        assert "bookings" in tables
        assert "payments" in tables

    async def test_session_factory_works(self, db_session):
        """Session should be able to execute queries."""
        from sqlalchemy import text
        result = await db_session.execute(text("SELECT 1"))
        assert result.scalar() == 1


class TestModelRelationships:
    """Test that model relationships are configured correctly."""

    async def test_user_has_bookings_relationship(self, db_session):
        from models import User
        user = User(tg_id=10000, full_name="Rel User")
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        assert hasattr(user, "bookings")

    async def test_club_has_bookings_relationship(self, db_session):
        from models import Club
        club = Club(name="Rel Club", city="T", address="A", driver_type="MOCK")
        db_session.add(club)
        await db_session.commit()
        await db_session.refresh(club)
        assert hasattr(club, "bookings")

    async def test_booking_references_user_and_club(self, db_session):
        from models import User, Club, Booking
        from utils.timezone import now_utc
        from datetime import timedelta

        user = User(tg_id=10001, full_name="Bk User")
        db_session.add(user)
        await db_session.flush()

        club = Club(name="Bk Club", city="T", address="B", driver_type="MOCK")
        db_session.add(club)
        await db_session.flush()

        now = now_utc()
        booking = Booking(user_id=user.id, club_id=club.id, computer_name="PC",
                          start_time=now, end_time=now + timedelta(hours=1))
        db_session.add(booking)
        await db_session.commit()
        await db_session.refresh(booking)

        assert booking.user_id == user.id
        assert booking.club_id == club.id

    async def test_payment_references_booking(self, db_session):
        from models import User, Club, Booking, Payment
        from utils.timezone import now_utc
        from datetime import timedelta

        user = User(tg_id=10002, full_name="Pay User")
        db_session.add(user)
        await db_session.flush()

        club = Club(name="Pay Club", city="T", address="C", driver_type="MOCK")
        db_session.add(club)
        await db_session.flush()

        now = now_utc()
        booking = Booking(user_id=user.id, club_id=club.id, computer_name="PC",
                          start_time=now, end_time=now + timedelta(hours=1))
        db_session.add(booking)
        await db_session.flush()

        payment = Payment(booking_id=booking.id, user_id=user.id,
                          amount=5000, provider="test")
        db_session.add(payment)
        await db_session.commit()
        await db_session.refresh(payment)

        assert payment.booking_id == booking.id


class TestExceptionModule:
    """Test custom exceptions."""

    def test_exceptions_importable(self):
        from exceptions import BookingError
        err = BookingError("test")
        assert str(err) == "test"
