"""
Tests for data models and timezone correctness.
"""
import pytest
from datetime import datetime, timedelta, timezone


class TestTimezoneUtils:
    """Verify timezone utility functions work correctly."""

    def test_now_utc_is_naive(self):
        from utils.timezone import now_utc
        dt = now_utc()
        assert dt.tzinfo is None, "now_utc() must return naive datetime"

    def test_now_tashkent_is_aware(self):
        from utils.timezone import now_tashkent
        dt = now_tashkent()
        assert dt.tzinfo is not None, "now_tashkent() must return aware datetime"

    def test_now_tashkent_is_utc_plus_5(self):
        from utils.timezone import now_tashkent, now_utc
        tash = now_tashkent()
        utc = now_utc()
        # Tashkent should be ~5 hours ahead of UTC (±1 sec tolerance)
        diff = tash.replace(tzinfo=None) - utc
        assert 4 * 3600 + 3590 < diff.total_seconds() < 5 * 3600 + 10

    def test_to_tashkent_naive_input(self):
        """Naive input is assumed UTC and converted to +5."""
        from utils.timezone import to_tashkent
        naive_utc = datetime(2026, 1, 1, 12, 0, 0)  # "noon UTC"
        result = to_tashkent(naive_utc)
        assert result.hour == 17  # 12 + 5 = 17

    def test_make_naive_utc_strips_tz(self):
        from utils.timezone import make_naive_utc, TASHKENT_TZ
        aware = datetime(2026, 1, 1, 17, 0, 0, tzinfo=TASHKENT_TZ)
        result = make_naive_utc(aware)
        assert result.tzinfo is None
        assert result.hour == 12  # 17 - 5 = 12 UTC


class TestUserModel:
    """Verify User model defaults."""

    async def test_user_created_at_is_utc(self, db_session):
        from models import User
        from utils.timezone import now_utc
        user = User(tg_id=999999, full_name="Test User")
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # created_at should be set and close to now_utc()
        assert user.created_at is not None
        now = now_utc()
        diff = abs((now - user.created_at.replace(tzinfo=None)).total_seconds())
        assert diff < 5, f"created_at should be within 5 seconds of now, got {diff}s"


class TestPromoCode:
    """Verify PromoCode.is_valid() works correctly."""

    async def test_valid_promo(self, db_session):
        from models import PromoCode
        from utils.timezone import now_utc
        promo = PromoCode(
            code="TEST10",
            discount_percent=10,
            is_active=True,
            expires_at=now_utc() + timedelta(hours=1),
        )
        assert promo.is_valid() is True

    async def test_expired_promo(self, db_session):
        from models import PromoCode
        from utils.timezone import now_utc
        promo = PromoCode(
            code="OLD",
            discount_percent=10,
            is_active=True,
            expires_at=now_utc() - timedelta(hours=1),
        )
        assert promo.is_valid() is False

    async def test_inactive_promo(self, db_session):
        from models import PromoCode
        promo = PromoCode(code="OFF", discount_percent=10, is_active=False)
        assert promo.is_valid() is False

    async def test_max_uses_reached(self, db_session):
        from models import PromoCode
        promo = PromoCode(
            code="MAXED", discount_percent=10, is_active=True,
            max_uses=5, uses_count=5,
        )
        assert promo.is_valid() is False


class TestBookingModel:
    """Verify Booking model."""

    async def test_booking_status_default(self, db_session):
        from models import User, Club, Booking
        from utils.timezone import now_utc

        user = User(tg_id=111, full_name="Booker")
        db_session.add(user)
        await db_session.flush()

        club = Club(name="Test Club", city="Tashkent", address="Test St",
                     driver_type="MOCK")
        db_session.add(club)
        await db_session.flush()

        now = now_utc()
        booking = Booking(
            user_id=user.id, club_id=club.id, computer_name="PC-1",
            start_time=now + timedelta(hours=2),
            end_time=now + timedelta(hours=3),
        )
        db_session.add(booking)
        await db_session.commit()
        await db_session.refresh(booking)

        assert booking.status == "CONFIRMED"
        assert booking.notification_sent is False
        assert booking.check_timeout is False
