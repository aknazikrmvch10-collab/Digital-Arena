"""
Payment service for Digital Arena.

Supports:
  - "test" mode: instant mock payments (no real money)
  - "click" mode: Click.uz integration (requires CLICK_MERCHANT_ID + CLICK_SERVICE_ID + CLICK_SECRET_KEY)
  - "payme" mode: Payme.uz integration (requires PAYME_MERCHANT_ID + PAYME_KEY)

Usage:
  from services.payment import PaymentService
  svc = PaymentService()
  result = await svc.create_payment(booking_id=1, user_id=1, amount=25000)
  # result = {"payment_id": 1, "checkout_url": "...", "provider": "test"}
"""
import os
import uuid
from datetime import datetime
from typing import Optional

from database import async_session_factory
from models import Payment, Booking
from sqlalchemy import select
from utils.timezone import now_utc
from utils.logging import get_logger

logger = get_logger(__name__)

# Read provider from env; default to "test"
PAYMENT_PROVIDER = os.getenv("PAYMENT_PROVIDER", "test")

# Click credentials (set in env when ready)
CLICK_MERCHANT_ID = os.getenv("CLICK_MERCHANT_ID")
CLICK_SERVICE_ID = os.getenv("CLICK_SERVICE_ID")
CLICK_SECRET_KEY = os.getenv("CLICK_SECRET_KEY")

# Payme credentials (set in env when ready)
PAYME_MERCHANT_ID = os.getenv("PAYME_MERCHANT_ID")
PAYME_KEY = os.getenv("PAYME_KEY")


class PaymentService:
    """Unified payment service with test/click/payme backends."""

    def __init__(self):
        self.provider = PAYMENT_PROVIDER
        logger.info("PaymentService initialized", provider=self.provider)

    async def create_payment(
        self,
        booking_id: int,
        user_id: int,
        amount: int,
    ) -> dict:
        """
        Create a payment for a booking.
        Returns: {"payment_id": int, "checkout_url": str, "provider": str}
        """
        async with async_session_factory() as session:
            # Create Payment record
            payment = Payment(
                booking_id=booking_id,
                user_id=user_id,
                amount=amount,
                provider=self.provider,
                status="pending",
            )
            session.add(payment)
            await session.commit()
            await session.refresh(payment)

            # Generate checkout URL based on provider
            if self.provider == "test":
                checkout_url = f"/api/payments/{payment.id}/test-pay"
            elif self.provider == "click":
                checkout_url = self._click_checkout_url(payment)
            elif self.provider == "payme":
                checkout_url = self._payme_checkout_url(payment)
            else:
                checkout_url = f"/api/payments/{payment.id}/test-pay"

            logger.info("Payment created",
                        payment_id=payment.id,
                        amount=amount,
                        provider=self.provider)

            return {
                "payment_id": payment.id,
                "checkout_url": checkout_url,
                "provider": self.provider,
                "amount": amount,
                "status": "pending",
            }

    async def confirm_payment(self, payment_id: int, transaction_id: Optional[str] = None) -> dict:
        """
        Mark payment as paid. Called by callback (Click/Payme) or test endpoint.
        """
        async with async_session_factory() as session:
            result = await session.execute(
                select(Payment).where(Payment.id == payment_id)
            )
            payment = result.scalar_one_or_none()
            if not payment:
                return {"success": False, "error": "Payment not found"}
            if payment.status == "paid":
                return {"success": True, "message": "Already paid"}

            payment.status = "paid"
            payment.paid_at = now_utc()
            if transaction_id:
                payment.transaction_id = transaction_id

            await session.commit()

            logger.info("Payment confirmed",
                        payment_id=payment_id,
                        transaction_id=transaction_id)

            return {"success": True, "payment_id": payment_id}

    async def get_payment_status(self, payment_id: int) -> dict:
        """Get current payment status."""
        async with async_session_factory() as session:
            result = await session.execute(
                select(Payment).where(Payment.id == payment_id)
            )
            payment = result.scalar_one_or_none()
            if not payment:
                return {"status": "not_found"}
            return {
                "payment_id": payment.id,
                "booking_id": payment.booking_id,
                "amount": payment.amount,
                "currency": payment.currency,
                "status": payment.status,
                "provider": payment.provider,
                "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
            }

    async def get_booking_payment(self, booking_id: int) -> Optional[dict]:
        """Get payment for a specific booking."""
        async with async_session_factory() as session:
            result = await session.execute(
                select(Payment).where(Payment.booking_id == booking_id)
                .order_by(Payment.created_at.desc()).limit(1)
            )
            payment = result.scalar_one_or_none()
            if not payment:
                return None
            return {
                "payment_id": payment.id,
                "amount": payment.amount,
                "status": payment.status,
                "provider": payment.provider,
            }

    # ==================== CLICK ====================

    def _click_checkout_url(self, payment: Payment) -> str:
        """Generate Click.uz checkout URL."""
        if not CLICK_MERCHANT_ID or not CLICK_SERVICE_ID:
            logger.warning("Click credentials not configured, falling back to test mode")
            return f"/api/payments/{payment.id}/test-pay"

        # Click checkout URL format
        return (
            f"https://my.click.uz/services/pay"
            f"?service_id={CLICK_SERVICE_ID}"
            f"&merchant_id={CLICK_MERCHANT_ID}"
            f"&amount={payment.amount}"
            f"&transaction_param={payment.id}"
            f"&return_url=https://arenaslot-123ab.web.app/miniapp/"
        )

    # ==================== PAYME ====================

    def _payme_checkout_url(self, payment: Payment) -> str:
        """Generate Payme checkout URL."""
        import base64
        if not PAYME_MERCHANT_ID:
            logger.warning("Payme credentials not configured, falling back to test mode")
            return f"/api/payments/{payment.id}/test-pay"

        # Payme checkout URL (base64 encoded params)
        params = f"m={PAYME_MERCHANT_ID};ac.order_id={payment.id};a={payment.amount * 100}"
        encoded = base64.b64encode(params.encode()).decode()
        return f"https://checkout.paycom.uz/{encoded}"


# Singleton instance
payment_service = PaymentService()
