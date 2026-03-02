"""
Reusable dependencies for API routes.
Provides helpers for auth, ownership verification, and pagination.
"""
from fastapi import HTTPException, Header, Depends, Query, Request
from sqlalchemy import select, and_, func
from database import async_session_factory
from models import User, Booking
from utils.telegram_auth import validate_telegram_data, validate_web_login_data
import json

async def get_current_user(
    request: Request, 
    x_telegram_init_data: str | None = Header(None),
    x_telegram_web_login: str | None = Header(None)
) -> dict:
    """
    Validates either Telegram Web App initData or Telegram Web Login data.
    Returns user info dictionary. Raises 401 if authentication fails.
    """
    user_data = None
    
    # 1. Try Telegram WebApp auth (Standard)
    if x_telegram_init_data:
        user_data = validate_telegram_data(x_telegram_init_data)
        
    # 2. Try Telegram Widget auth (Standalone PWA)
    elif x_telegram_web_login:
        try:
            web_auth_payload = json.loads(x_telegram_web_login)
            user_data = validate_web_login_data(web_auth_payload)
        except json.JSONDecodeError:
            pass # Fall through to 401
            
    if not user_data:
        raise HTTPException(
            status_code=401, 
            detail="Authentication required (Missing or Invalid Headers)"
        )
    
    return user_data


async def verify_booking_owner(
    booking_id: int,
    user_data: dict = Depends(get_current_user)
) -> Booking:
    """
    Verify that the booking exists and belongs to the authenticated user.
    Returns the Booking object if valid.
    Raises 404 if booking not found or not owned by user (prevents IDOR).
    """
    user_id = user_data["id"]
    
    async with async_session_factory() as session:
        # Find user by Telegram ID
        user_result = await session.execute(
            select(User).where(User.tg_id == user_id)
        )
        user = user_result.scalars().first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Find booking with IDOR protection
        result = await session.execute(
            select(Booking).where(
                and_(
                    Booking.id == booking_id,
                    Booking.user_id == user.id
                )
            )
        )
        booking = result.scalars().first()
        
        if not booking:
            raise HTTPException(
                status_code=404,
                detail="Booking not found or access denied"
            )
        
        return booking


class PaginationParams:
    """Pagination parameters for list endpoints."""
    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number"),
        limit: int = Query(10, ge=1, le=100, description="Items per page")
    ):
        self.page = page
        self.limit = limit
        self.offset = (page - 1) * limit
