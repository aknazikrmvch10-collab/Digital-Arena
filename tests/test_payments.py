"""
Tests for payment service and payment API endpoints.
"""
import pytest
from datetime import timedelta


class TestPaymentService:
    """Test PaymentService directly."""

    async def test_create_payment(self, db_session):
        from services.payment import PaymentService
        from models import User, Club, Booking
        from utils.timezone import now_utc

        # Create prerequisite data
        user = User(tg_id=555, full_name="Payer")
        db_session.add(user)
        await db_session.flush()

        club = Club(name="Pay Club", city="T", address="A", driver_type="MOCK")
        db_session.add(club)
        await db_session.flush()

        now = now_utc()
        booking = Booking(user_id=user.id, club_id=club.id, computer_name="PC-1",
                          start_time=now + timedelta(hours=2),
                          end_time=now + timedelta(hours=3))
        db_session.add(booking)
        await db_session.commit()

        svc = PaymentService()
        result = await svc.create_payment(
            booking_id=booking.id, user_id=user.id, amount=25000
        )

        assert result["payment_id"] is not None
        assert result["amount"] == 25000
        assert result["provider"] == "test"
        assert result["status"] == "pending"
        assert "/test-pay" in result["checkout_url"]

    async def test_confirm_payment(self, db_session):
        from services.payment import PaymentService
        from models import User, Club, Booking, Payment
        from utils.timezone import now_utc

        user = User(tg_id=556, full_name="Payer2")
        db_session.add(user)
        await db_session.flush()

        club = Club(name="Pay Club 2", city="T", address="B", driver_type="MOCK")
        db_session.add(club)
        await db_session.flush()

        now = now_utc()
        booking = Booking(user_id=user.id, club_id=club.id, computer_name="PC-2",
                          start_time=now + timedelta(hours=2),
                          end_time=now + timedelta(hours=3))
        db_session.add(booking)
        await db_session.flush()

        payment = Payment(booking_id=booking.id, user_id=user.id,
                          amount=30000, provider="test", status="pending")
        db_session.add(payment)
        await db_session.commit()

        svc = PaymentService()
        result = await svc.confirm_payment(payment.id, transaction_id="TEST-XYZ")
        assert result["success"] is True

    async def test_confirm_nonexistent_payment(self, db_session):
        from services.payment import PaymentService
        svc = PaymentService()
        result = await svc.confirm_payment(99999)
        assert result["success"] is False
        assert "not found" in result["error"].lower()

    async def test_double_confirm_idempotent(self, db_session):
        from services.payment import PaymentService
        from models import User, Club, Booking, Payment
        from utils.timezone import now_utc

        user = User(tg_id=557, full_name="Payer3")
        db_session.add(user)
        await db_session.flush()

        club = Club(name="Pay Club 3", city="T", address="C", driver_type="MOCK")
        db_session.add(club)
        await db_session.flush()

        now = now_utc()
        booking = Booking(user_id=user.id, club_id=club.id, computer_name="PC-3",
                          start_time=now + timedelta(hours=2),
                          end_time=now + timedelta(hours=3))
        db_session.add(booking)
        await db_session.flush()

        payment = Payment(booking_id=booking.id, user_id=user.id,
                          amount=10000, provider="test", status="pending")
        db_session.add(payment)
        await db_session.commit()

        svc = PaymentService()
        r1 = await svc.confirm_payment(payment.id)
        assert r1["success"] is True

        # Second confirm should also succeed (idempotent)
        r2 = await svc.confirm_payment(payment.id)
        assert r2["success"] is True
        assert "already" in r2.get("message", "").lower()

    async def test_get_payment_status(self, db_session):
        from services.payment import PaymentService
        from models import User, Club, Booking, Payment
        from utils.timezone import now_utc

        user = User(tg_id=558, full_name="Status")
        db_session.add(user)
        await db_session.flush()

        club = Club(name="Status Club", city="T", address="D", driver_type="MOCK")
        db_session.add(club)
        await db_session.flush()

        now = now_utc()
        booking = Booking(user_id=user.id, club_id=club.id, computer_name="PC-S",
                          start_time=now + timedelta(hours=2),
                          end_time=now + timedelta(hours=3))
        db_session.add(booking)
        await db_session.flush()

        payment = Payment(booking_id=booking.id, user_id=user.id,
                          amount=5000, provider="test", status="pending")
        db_session.add(payment)
        await db_session.commit()

        svc = PaymentService()
        status = await svc.get_payment_status(payment.id)
        assert status["status"] == "pending"
        assert status["amount"] == 5000

    async def test_get_nonexistent_payment_status(self, db_session):
        from services.payment import PaymentService
        svc = PaymentService()
        status = await svc.get_payment_status(99999)
        assert status["status"] == "not_found"

    async def test_get_booking_payment(self, db_session):
        from services.payment import PaymentService
        from models import User, Club, Booking, Payment
        from utils.timezone import now_utc

        user = User(tg_id=559, full_name="BookPay")
        db_session.add(user)
        await db_session.flush()

        club = Club(name="BookPay Club", city="T", address="E", driver_type="MOCK")
        db_session.add(club)
        await db_session.flush()

        now = now_utc()
        booking = Booking(user_id=user.id, club_id=club.id, computer_name="PC-BP",
                          start_time=now + timedelta(hours=2),
                          end_time=now + timedelta(hours=3))
        db_session.add(booking)
        await db_session.flush()

        payment = Payment(booking_id=booking.id, user_id=user.id,
                          amount=15000, provider="test", status="paid")
        db_session.add(payment)
        await db_session.commit()

        svc = PaymentService()
        result = await svc.get_booking_payment(booking.id)
        assert result is not None
        assert result["status"] == "paid"

    async def test_get_booking_payment_none(self, db_session):
        from services.payment import PaymentService
        svc = PaymentService()
        result = await svc.get_booking_payment(99999)
        assert result is None


class TestPaymentAPI:
    """Test payment API endpoints."""

    async def test_test_pay_endpoint(self, client, db_session):
        from models import User, Club, Booking, Payment
        from utils.timezone import now_utc

        user = User(tg_id=600, full_name="API Pay")
        db_session.add(user)
        await db_session.flush()

        club = Club(name="API Club", city="T", address="F", driver_type="MOCK")
        db_session.add(club)
        await db_session.flush()

        now = now_utc()
        booking = Booking(user_id=user.id, club_id=club.id, computer_name="PC-A",
                          start_time=now + timedelta(hours=2),
                          end_time=now + timedelta(hours=3))
        db_session.add(booking)
        await db_session.flush()

        payment = Payment(booking_id=booking.id, user_id=user.id,
                          amount=20000, provider="test", status="pending")
        db_session.add(payment)
        await db_session.commit()

        r = await client.post(f"/api/payments/{payment.id}/test-pay")
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True

    async def test_get_payment_status_api(self, client, db_session):
        from models import User, Club, Booking, Payment
        from utils.timezone import now_utc

        user = User(tg_id=601, full_name="Status API")
        db_session.add(user)
        await db_session.flush()

        club = Club(name="Status API Club", city="T", address="G", driver_type="MOCK")
        db_session.add(club)
        await db_session.flush()

        now = now_utc()
        booking = Booking(user_id=user.id, club_id=club.id, computer_name="PC-SA",
                          start_time=now + timedelta(hours=2),
                          end_time=now + timedelta(hours=3))
        db_session.add(booking)
        await db_session.flush()

        payment = Payment(booking_id=booking.id, user_id=user.id,
                          amount=8000, provider="test", status="pending")
        db_session.add(payment)
        await db_session.commit()

        r = await client.get(f"/api/payments/{payment.id}")
        assert r.status_code == 200
        assert r.json()["status"] == "pending"

    async def test_get_nonexistent_payment_api(self, client):
        r = await client.get("/api/payments/99999")
        assert r.status_code == 404
