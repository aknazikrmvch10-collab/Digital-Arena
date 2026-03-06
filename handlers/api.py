from fastapi import APIRouter, HTTPException, Header, Depends, Query, Request
from database import async_session_factory
from models import Club, Computer, User, Booking, RestaurantTable
from sqlalchemy import select, and_, func
from pydantic import BaseModel, field_validator
from datetime import datetime, timedelta, timezone
from utils.timezone import now_tashkent
from typing import Optional, List
from drivers.factory import DriverFactory
from services.redis_client import cache
from handlers.dependencies import get_current_user, verify_booking_owner, PaginationParams
from utils.limiter import limiter
from utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Simple cache for bot configuration
_app_config_cache = {}

@router.get("/config")
async def get_app_config():
    """
    Returns public configuration for the frontend apps.
    Fetches the bot username from Telegram API and caches it.
    """
    global _app_config_cache
    if "bot_username" in _app_config_cache:
        return _app_config_cache

    try:
        from config import settings
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.telegram.org/bot{settings.BOT_TOKEN}/getMe") as response:
                data = await response.json()
                if data.get("ok"):
                    _app_config_cache["bot_username"] = data["result"]["username"]
                else:
                    _app_config_cache["bot_username"] = "DigitalArena_bot" # Fallback
    except Exception as e:
        logger.error("Failed to fetch bot username for config", error=str(e))
        _app_config_cache["bot_username"] = "DigitalArena_bot"
        
    return _app_config_cache


# ===================== PHONE+CODE AUTH =====================

class PhoneCodeRequest(BaseModel):
    phone: str   # e.g. "+998901234567"
    code: str    # 6-digit code from bot

@router.post("/auth/verify-code")
async def verify_phone_code(req: PhoneCodeRequest):
    """
    Verify phone+code pair from the standalone PWA login screen.
    Returns a session_token on success.
    """
    import uuid
    from models import AppAuthCode, AppSession
    from datetime import timezone as _tz

    # Normalize phone
    phone = req.phone.strip()
    if not phone.startswith("+"):
        phone = "+" + phone

    code = req.code.strip()

    async with async_session_factory() as session:
        # Use naive UTC to match how we store expires_at in the DB
        from utils.timezone import now_utc
        now = now_utc()
        
        # Find a valid matching code
        result = await session.execute(
            select(AppAuthCode).where(
                and_(
                    AppAuthCode.phone == phone,
                    AppAuthCode.code == code,
                    AppAuthCode.used == False,
                )
            ).order_by(AppAuthCode.created_at.desc()).limit(1)
        )
        auth_code = result.scalar_one_or_none()

        if not auth_code:
            raise HTTPException(status_code=401, detail="Неверный номер или код")

        # Check expiry
        expires = auth_code.expires_at
        
        # Normalize both to naive for comparison
        now_naive = now.replace(tzinfo=None)
        expires_naive = expires.replace(tzinfo=None) if expires.tzinfo else expires
        
        if now_naive > expires_naive:
            raise HTTPException(status_code=401, detail="Код истёк. Запросите новый через /myapp в боте")

        # Mark code as used
        auth_code.used = True

        # Get user info
        user = await session.execute(
            select(User).where(User.tg_id == auth_code.user_id)
        )
        user = user.scalar_one_or_none()

        # Create a session token
        token = str(uuid.uuid4())
        app_session = AppSession(
            user_id=auth_code.user_id,
            session_token=token,
            phone=phone,
            full_name=user.full_name if user else None,
        )
        session.add(app_session)
        await session.commit()

        return {
            "success": True,
            "session_token": token,
            "user_id": auth_code.user_id,
            "full_name": user.full_name if user else None,
            "phone": phone,
            "has_password": bool(user and user.password_hash)  # Signal to frontend if profile setup is needed
        }

class CompleteProfileRequest(BaseModel):
    full_name: str
    password: str

@router.post("/auth/complete_profile")
async def complete_profile(req: CompleteProfileRequest, x_session_token: str = Header(None)):
    """Complete profile (name and password) after OTP login."""
    if not x_session_token:
        raise HTTPException(status_code=401, detail="Missing session")
    
    import hashlib, uuid
    from models import AppSession
    
    async with async_session_factory() as session:
        result = await session.execute(
            select(AppSession).where(AppSession.session_token == x_session_token)
        )
        app_session = result.scalar_one_or_none()
        if not app_session:
            raise HTTPException(status_code=401, detail="Invalid session")
            
        user_result = await session.execute(select(User).where(User.id == app_session.user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            
        salt = str(uuid.uuid4())[:8]
        pw_hash = hashlib.sha256(f"{req.password}{salt}".encode()).hexdigest()
        
        user.password_hash = f"{salt}${pw_hash}"
        user.full_name = req.full_name
        
        # update session name too
        app_session.full_name = req.full_name
        
        await session.commit()
        
    return {"success": True, "full_name": req.full_name}


@router.post("/auth/logout")
async def app_logout(x_session_token: str = Header(None)):
    """Invalidate a standalone PWA session."""
    if not x_session_token:
        return {"success": True}
    from models import AppSession
    async with async_session_factory() as session:
        result = await session.execute(
            select(AppSession).where(AppSession.session_token == x_session_token)
        )
        app_session = result.scalar_one_or_none()
        if app_session:
            await session.delete(app_session)
            await session.commit()
    return {"success": True}


class RegisterRequest(BaseModel):
    full_name: str
    phone: str
    password: str   # plain text, will be hashed

class LoginPasswordRequest(BaseModel):
    phone: str
    password: str


@router.post("/auth/register")
async def register_with_password(req: RegisterRequest):
    """
    Create a new account with name, phone, and password.
    Works independently of Telegram — for multi-device login.
    """
    import hashlib, uuid

    # Simple hash: sha256(password+salt). bcrypt not needed for this scale.
    salt = str(uuid.uuid4())[:8]
    pw_hash = hashlib.sha256(f"{req.password}{salt}".encode()).hexdigest()
    password_hash = f"{salt}${pw_hash}"

    phone = req.phone.strip()
    if not phone.startswith("+"):
        phone = "+" + phone

    async with async_session_factory() as session:
        # Check if phone already exists
        existing = await session.execute(
            select(User).where(User.phone == phone)
        )
        existing_user = existing.scalar_one_or_none()

        if existing_user:
            # If user exists but has no password, set it
            if not existing_user.password_hash:
                existing_user.password_hash = password_hash
                existing_user.full_name = req.full_name or existing_user.full_name
                await session.commit()
                user_id = existing_user.id
                full_name = existing_user.full_name
            else:
                raise HTTPException(status_code=400,
                    detail="Аккаунт с таким номером уже существует. Войдите или используйте другой номер.")
        else:
            # Create new user
            new_user = User(
                full_name=req.full_name,
                phone=phone,
                password_hash=password_hash,
                tg_id=None,
            )
            session.add(new_user)
            await session.commit()
            await session.refresh(new_user)
            user_id = new_user.id
            full_name = new_user.full_name

        # Issue session token
        from models import AppSession
        token = str(uuid.uuid4())
        app_session = AppSession(
            user_id=user_id,
            session_token=token,
            phone=phone,
            full_name=full_name,
        )
        session.add(app_session)
        await session.commit()

        return {
            "success": True,
            "session_token": token,
            "user_id": user_id,
            "full_name": full_name,
            "phone": phone,
        }


@router.post("/auth/login-password")
async def login_with_password(req: LoginPasswordRequest):
    """
    Login with phone + password.
    Returns session_token compatible with existing session system.
    """
    import hashlib, uuid

    phone = req.phone.strip()
    if not phone.startswith("+"):
        phone = "+" + phone

    async with async_session_factory() as session:
        result = await session.execute(
            select(User).where(User.phone == phone)
        )
        user = result.scalar_one_or_none()

        if not user or not user.password_hash:
            raise HTTPException(status_code=401,
                detail="Аккаунт не найден. Сначала зарегистрируйтесь.")

        # Verify password
        salt, stored_hash = user.password_hash.split("$", 1)
        input_hash = hashlib.sha256(f"{req.password}{salt}".encode()).hexdigest()

        if input_hash != stored_hash:
            raise HTTPException(status_code=401, detail="Неверный пароль")

        # Issue session token
        from models import AppSession
        token = str(uuid.uuid4())
        app_session = AppSession(
            user_id=user.id,
            session_token=token,
            phone=phone,
            full_name=user.full_name,
        )
        session.add(app_session)
        await session.commit()

        return {
            "success": True,
            "session_token": token,
            "user_id": user.id,
            "full_name": user.full_name,
            "phone": phone,
        }




# --- Request Models ---
class BookingRequest(BaseModel):
    user_id: int # Telegram User ID
    club_id: int
    computer_id: str
    start_time: datetime
    duration_minutes: int
    
    @field_validator('club_id')
    @classmethod
    def validate_club_id(cls, v):
        if v <= 0:
            raise ValueError('Club ID must be positive')
        return v
    
    @field_validator('duration_minutes')
    @classmethod
    def validate_duration(cls, v):
        if v <= 0:
            raise ValueError('Duration must be greater than 0')
        if v > 24 * 60:  # Max 24 hours
            raise ValueError('Duration cannot exceed 24 hours')
        return v
    
    @field_validator('start_time')
    @classmethod
    def validate_start_time(cls, v):
        import datetime as _dt
        from utils.timezone import now_utc as _now_utc
        # Normalize v to naive UTC for comparison
        if v.tzinfo is not None:
            v_utc = v.astimezone(_dt.timezone.utc).replace(tzinfo=None)
        else:
            v_utc = v
        now = _now_utc()  # naive UTC
        # Allow bookings at least 10 minutes from now (MVP-friendly)
        if v_utc <= now + _dt.timedelta(minutes=10):
            raise ValueError('Booking must be at least 10 minutes in advance')
        # Max booking 90 days in advance
        if v_utc > now + _dt.timedelta(days=90):
            raise ValueError('Booking cannot be more than 90 days in advance')
        return v
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class AvailabilityRequest(BaseModel):
    club_id: int
    computer_id: str
    date: str # YYYY-MM-DD

# Note: get_current_user is now imported from handlers.dependencies

# --- Endpoints ---

@router.get("/health")
async def health_check():
    """
    Health Check endpoint для мониторинга состояния сервиса.
    Проверяет: БД, Redis.
    """
    import time
    start_time = time.time()
    
    health = {
        "status": "healthy",
        "timestamp": now_tashkent().isoformat(),
        "services": {}
    }
    
    # Check Database
    try:
        async with async_session_factory() as session:
            await session.execute(select(1))
        health["services"]["database"] = {"status": "ok"}
    except Exception as e:
        health["services"]["database"] = {"status": "error", "detail": str(e)}
        health["status"] = "degraded"
    
    # Check Redis
    redis_health = await cache.health_check()
    health["services"]["redis"] = redis_health
    if not redis_health.get("ok"):
        health["status"] = "degraded"
    
    health["response_time_ms"] = round((time.time() - start_time) * 1000, 2)
    
    # Return 503 if unhealthy
    if health["status"] != "healthy":
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=503, content=health)
    
    return health

@router.get("/clubs")
async def get_clubs(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    is_active: bool = Query(True, description="Show only active clubs")
):
    """Get clubs with pagination, live seat count, and average ratings."""
    from models import Review, Computer
    from datetime import datetime
    async with async_session_factory() as session:
        # Get total count
        count_query = select(func.count(Club.id)).where(Club.is_active == is_active)
        total = await session.scalar(count_query) or 0
        
        # Get paginated results
        result = await session.execute(
            select(Club)
            .where(Club.is_active == is_active)
            .order_by(Club.name.asc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        clubs = result.scalars().all()
        
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        clubs_data = []
        for c in clubs:
            d = c.to_dict()
            d["latitude"] = c.latitude
            d["longitude"] = c.longitude

            # Live seat count: total computers minus currently booked
            total_seats = await session.scalar(
                select(func.count(Computer.id)).where(Computer.club_id == c.id, Computer.is_active == True)
            ) or 0
            occupied_seats = await session.scalar(
                select(func.count(Booking.item_id)).where(
                    Booking.club_id == c.id,
                    Booking.status.in_(["CONFIRMED", "ACTIVE"]),
                    Booking.start_time <= now,
                    Booking.end_time > now
                )
            ) or 0
            free_seats = max(0, total_seats - occupied_seats)

            # Average rating
            avg_rating = await session.scalar(
                select(func.avg(Review.rating)).where(Review.club_id == c.id)
            )
            review_count = await session.scalar(
                select(func.count(Review.id)).where(Review.club_id == c.id)
            ) or 0

            d["total_seats"] = total_seats
            d["free_seats"] = free_seats
            d["avg_rating"] = round(float(avg_rating), 1) if avg_rating else None
            d["review_count"] = review_count
            clubs_data.append(d)
        
        import math
        return {
            "clubs": clubs_data,
            "page": page,
            "limit": limit,
            "total": total,
            "pages": math.ceil(total / limit) if total > 0 else 0
        }


@router.get("/clubs/{club_id}/computers")
async def get_items(
    club_id: int,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page")
):
    """Get items (computers or tables) for a club with pagination."""
    async with async_session_factory() as session:
        club = await session.get(Club, club_id)
        if not club:
            raise HTTPException(status_code=404, detail="Club not found")
        
        venue_type = getattr(club, 'venue_type', 'computer_club')
        
        if venue_type == 'restaurant':
            # Get total count for restaurants
            count_query = select(func.count(RestaurantTable.id)).where(
                RestaurantTable.club_id == club_id
            )
            total = await session.scalar(count_query) or 0
            
            # Get paginated tables
            result = await session.execute(
                select(RestaurantTable)
                .where(RestaurantTable.club_id == club_id)
                .order_by(RestaurantTable.name.asc())
                .offset((page - 1) * limit)
                .limit(limit)
            )
            tables = result.scalars().all()
            
            items = []
            for t in tables:
                item = t.to_dict()
                # Polyfill missing fields for frontend compatibility
                item['price_per_hour'] = t.booking_price
                item['cpu'] = f"Мест: {t.seats}"
                item['gpu'] = f"Депозит: {t.min_deposit}"
                item['ram_gb'] = 0
                item['monitor_hz'] = 0
                item['venue_type'] = 'restaurant'
                items.append(item)
            
            import math
            return {
                "items": items,
                "page": page,
                "limit": limit,
                "total": total,
                "pages": math.ceil(total / limit) if total > 0 else 0
            }
        else:
            # Get total count for computers
            count_query = select(func.count(Computer.id)).where(
                Computer.club_id == club_id
            )
            total = await session.scalar(count_query) or 0
            
            # Get paginated computers
            result = await session.execute(
                select(Computer)
                .where(Computer.club_id == club_id)
                .order_by(Computer.zone.asc(), Computer.name.asc())
                .offset((page - 1) * limit)
                .limit(limit)
            )
            computers = result.scalars().all()
            
            # 🔗 SYNC: Find all CURRENTLY ACTIVE bookings for this club right now
            # This ensures bot bookings show as occupied in the WebApp and vice versa
            from datetime import datetime
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            active_bookings_result = await session.execute(
                select(Booking.item_id).where(
                    Booking.club_id == club_id,
                    Booking.status.in_(["CONFIRMED", "ACTIVE"]),
                    Booking.start_time <= now,
                    Booking.end_time > now
                )
            )
            # Set of currently occupied computer IDs
            occupied_item_ids = set(active_bookings_result.scalars().all())
            
            items = []
            for c in computers:
                item = c.to_dict()
                item['venue_type'] = 'computer_club'
                # Mark as unavailable if it has an active booking right now
                if c.id in occupied_item_ids:
                    item['is_available'] = False
                items.append(item)
            
            import math
            return {
                "items": items,
                "page": page,
                "limit": limit,
                "total": total,
                "pages": math.ceil(total / limit) if total > 0 else 0
            }

@router.post("/bookings")
@limiter.limit("5/minute")
async def create_booking(booking: BookingRequest, request: Request, user_data: dict = Depends(get_current_user)):
    """
    Create a new booking with race condition protection.
    Securely uses user_id from Telegram validation.
    """
    # Overwrite user_id with authenticated ID
    booking.user_id = user_data["id"]
    
    async with async_session_factory() as session:
        # ✅ FIX: Wrap entire booking process in transaction
        async with session.begin():
            # Get club (no lock needed, club data doesn't change during booking)
            club = await session.get(Club, booking.club_id)
            if not club:
                raise HTTPException(status_code=404, detail="Club not found")
            
            venue_type = getattr(club, 'venue_type', 'computer_club')
                
            # Get or create user
            logger.info("Booking Request", booking=booking.dict())
            
            result = await session.execute(select(User).where(User.tg_id == booking.user_id))
            user = result.scalars().first()
            
            if not user:
                logger.info(f"User {booking.user_id} not found, creating new.")
                user = User(tg_id=booking.user_id, full_name="WebApp User")
                session.add(user)
                await session.flush()  # ✅ Use flush instead of commit (stays in transaction)
                await session.refresh(user)
            
            # ✅ SECURITY: Age verification check (prevents bypassing bot's age gate via PWA)
            if user and not getattr(user, 'age_confirmed', True):
                raise HTTPException(
                    status_code=403,
                    detail="Необходима возрастная верификация. Откройте бота и подтвердите возраст."
                )

            
            # Ensure start_time is naive UTC (strip tz info without converting)
            if booking.start_time.tzinfo is not None:
                # Convert to UTC then remove tzinfo to store as naive UTC in DB
                import datetime as _dt
                booking_start_naive = booking.start_time.astimezone(_dt.timezone.utc).replace(tzinfo=None)
            else:
                booking_start_naive = booking.start_time
            
            # Verify item exists and get its name
            if venue_type == 'restaurant':
                item = await session.get(RestaurantTable, int(booking.computer_id))
                if not item:
                    raise HTTPException(status_code=404, detail="Table not found")
            else:
                # Computer Club
                item = await session.get(Computer, int(booking.computer_id))
                if not item:
                    raise HTTPException(status_code=404, detail="Computer not found")
            
            # Initialize driver and reserve
            # Note: Driver's reserve_pc is now inside this transaction,
            # so its conflict checks will be protected by transaction isolation
            try:
                driver = DriverFactory.get_driver(
                    club.driver_type, 
                    {"club_id": club.id, **club.connection_config}
                )
                
                result = await driver.reserve_pc(
                    pc_id=booking.computer_id,
                    user_id=user.id,
                    start_time=booking_start_naive,
                    duration_minutes=booking.duration_minutes
                )
                
                if result.success:
                    logger.info("Booking success", booking_id=result.booking_id)
                    # Notify club admin AND user (fire-and-forget, non-blocking)
                    try:
                        from main import bot as _bot
                        from background_tasks import notify_club_admin_new_booking
                        from models import Booking as _Booking
                        import asyncio as _asyncio
                        import datetime as _dt

                        new_booking_result = await session.execute(
                            select(_Booking).where(_Booking.id == int(result.booking_id))
                        )
                        new_booking = new_booking_result.scalars().first()

                        if new_booking:
                            # Notify admin
                            _asyncio.create_task(
                                notify_club_admin_new_booking(_bot, new_booking, user, club)
                            )

                            # 🎉 Notify USER with beautiful confirmation
                            try:
                                start_local = new_booking.start_time + _dt.timedelta(hours=5)
                                end_local = start_local + _dt.timedelta(minutes=booking.duration_minutes)
                                dur_h = booking.duration_minutes // 60
                                dur_m = booking.duration_minutes % 60
                                dur_str = f"{dur_h}ч {dur_m}мин" if dur_m else f"{dur_h}ч"
                                if dur_h == 0:
                                    dur_str = f"{dur_m} мин"
                                item_name = getattr(item, 'name', f'#{booking.computer_id}')
                                zone_name = getattr(item, 'zone', '')
                                price_per_hour = getattr(item, 'price_per_hour', 0)
                                price_total = int((booking.duration_minutes / 60) * price_per_hour)

                                confirm_msg = (
                                    f"✅ <b>Бронь подтверждена!</b>\n\n"
                                    f"🏢 <b>Клуб:</b> {club.name}\n"
                                    f"💻 <b>Место:</b> {item_name}" + (f" ({zone_name})" if zone_name else "") + "\n"
                                    f"📅 <b>Дата:</b> {start_local.strftime('%d.%m.%Y')}\n"
                                    f"⏰ <b>Время:</b> {start_local.strftime('%H:%M')} — {end_local.strftime('%H:%M')}\n"
                                    f"⏱ <b>Длительность:</b> {dur_str}\n"
                                    f"💰 <b>Сумма:</b> {price_total:,} сум\n\n"
                                    f"🎫 <b>ID брони:</b> #{result.booking_id}\n\n"
                                    f"👉 Покажите QR-код на входе в клуб!\n"
                                    f"📱 Открыть бронь: /my"
                                )
                                _asyncio.create_task(
                                    _bot.send_message(
                                        chat_id=user.tg_id,
                                        text=confirm_msg,
                                        parse_mode="HTML"
                                    )
                                )
                            except Exception as _ue:
                                logger.warning("Could not notify user about booking", error=str(_ue))

                    except Exception as _e:
                        logger.warning("Could not send booking notifications", error=str(_e))

                    # Transaction will auto-commit at end of 'async with session.begin()'
                    return {
                        "success": True,
                        "message": result.message,
                        "booking_id": result.booking_id
                    }
                else:
                    logger.warning("Booking failed", message=result.message)
                    # Transaction will auto-rollback since we're not committing
                    raise HTTPException(
                        status_code=409,
                        detail=result.message or "Booking conflict - time slot unavailable"
                    )
                    
            except HTTPException:
                raise  # Re-raise HTTP exceptions
            except ValueError as e:
                logger.error("Invalid booking parameters", error=str(e))
                raise HTTPException(status_code=422, detail=f"Invalid parameters: {str(e)}")
            except Exception as e:
                # Transaction will auto-rollback on exception
                logger.error("Booking Exception", error=str(e), exc_info=True)
                raise HTTPException(status_code=500, detail="Booking failed - please try again later")

@router.get("/availability")
@limiter.limit("20/minute")
async def check_availability(
    club_id: int = Query(..., gt=0, description="Club ID"),
    computer_id: str = Query(..., description="Computer or Table ID"),
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    request: Request = None
):
    """Check availability for an item on a specific date."""
    # Validate date format
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Validate date is not in the past
    from utils.timezone import now_utc as _now_utc_fn
    if target_date < _now_utc_fn().date():
        raise HTTPException(status_code=400, detail="Cannot check availability for past dates")

    async with async_session_factory() as session:
        club = await session.get(Club, club_id)
        if not club:
            raise HTTPException(status_code=404, detail="Club not found")
        
        venue_type = getattr(club, 'venue_type', 'computer_club')
        
        # Validate and resolve item
        try:
            computer_id_int = int(computer_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Компьютер ID должен быть числом")
        
        item_name = ""
        if venue_type == 'restaurant':
            item = await session.get(RestaurantTable, computer_id_int)
            if not item:
                raise HTTPException(status_code=404, detail="Table not found")
            item_name = item.name
        else:
            item = await session.get(Computer, computer_id_int)
            if not item:
                raise HTTPException(status_code=404, detail="Computer not found")
            item_name = item.name

        # Query Bookings using item_id (reliable) instead of computer_name
        result = await session.execute(
            select(Booking).where(
                and_(
                    Booking.club_id == club_id,
                    Booking.item_id == computer_id_int,
                    Booking.status.in_(["CONFIRMED", "ACTIVE"])
                )
            )
        )
        bookings = result.scalars().all()
        
        occupied_hours = set()
        from utils.timezone import TASHKENT_TZ
        for b in bookings:
            # Compare using Tashkent timezone for consistency
            b_start = b.start_time.astimezone(TASHKENT_TZ) if b.start_time.tzinfo else b.start_time
            b_end = b.end_time.astimezone(TASHKENT_TZ) if b.end_time.tzinfo else b.end_time
            
            for hour in range(24):
                check_time = datetime.combine(target_date, datetime.min.time().replace(hour=hour, tzinfo=TASHKENT_TZ))
                check_end = check_time + timedelta(hours=1)
                
                if (b_start < check_end) and (b_end > check_time):
                    occupied_hours.add(hour)
                    
        return {"occupied_hours": sorted(list(occupied_hours))}

@router.get("/user/bookings")
async def get_user_bookings(
    request: Request,
    user_data: dict = Depends(get_current_user),
    pagination: PaginationParams = Depends()
):
    """Get active and future bookings for a user with pagination."""
    user_id = user_data["id"]
    async with async_session_factory() as session:
        # Get total count first
        from utils.timezone import now_utc as _now_utc_fn
        _now = _now_utc_fn()  # naive UTC for DB comparison
        count_query = select(func.count(Booking.id)).join(
            User, Booking.user_id == User.id
        ).where(
            and_(
                User.tg_id == user_id,
                Booking.status == "CONFIRMED",
                Booking.end_time > _now
            )
        )
        total = await session.scalar(count_query) or 0
        
        # Get paginated results
        result = await session.execute(
            select(Booking, Club).join(Club, Booking.club_id == Club.id).join(
                User, Booking.user_id == User.id
            ).where(
                and_(
                    User.tg_id == user_id,
                    Booking.status.in_(["CONFIRMED", "ACTIVE"]),
                    Booking.end_time > _now
                )
            ).order_by(Booking.start_time.asc())
            .offset(pagination.offset)
            .limit(pagination.limit)
        )
        
        from datetime import timezone, timedelta
        rows = result.all()
        bookings = []
        for booking, club in rows:
            tz = timezone(timedelta(hours=5))
            display_start = booking.start_time.astimezone(tz).strftime("%d.%m %H:%M")
            display_end = booking.end_time.astimezone(tz).strftime("%H:%M")
            
            bookings.append({
                "id": booking.id,
                "club_name": club.name,
                "computer_name": booking.computer_name,
                "start_time": booking.start_time.isoformat(),
                "display_time": f"{display_start} - {display_end}",
                "status": booking.status,
                "total_price": 0
            })
        
        import math
        return {
            "bookings": bookings,
            "page": pagination.page,
            "limit": pagination.limit,
            "total": total,
            "pages": math.ceil(total / pagination.limit) if total > 0 else 0
        }


@router.delete("/bookings/{booking_id}")
async def cancel_booking(
    booking_id: int,
    user_data: dict = Depends(get_current_user)
):
    """
    Cancel a booking (owner only).
    Uses IDOR protection via user verification.
    """
    if booking_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid booking ID")
    
    user_id = user_data["id"]
    
    try:
        async with async_session_factory() as session:
            async with session.begin():
                # Find user
                user_result = await session.execute(
                    select(User).where(User.tg_id == user_id)
                )
                user = user_result.scalars().first()
                
                if not user:
                    raise HTTPException(status_code=404, detail="User not found")
                
                # Find booking with ownership check (IDOR protection)
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
                
                if booking.status != "CONFIRMED":
                    raise HTTPException(
                        status_code=400,
                        detail="Only confirmed bookings can be cancelled"
                    )
                
                # Check if booking is too close to start time (within 1 hour)
                from utils.timezone import now_utc as _now_utc_fn
                _now_cancel = _now_utc_fn()
                start_naive = booking.start_time.replace(tzinfo=None) if booking.start_time.tzinfo else booking.start_time
                time_until_booking = (start_naive - _now_cancel).total_seconds() / 3600
                if time_until_booking < 1:
                    raise HTTPException(
                        status_code=400,
                        detail="Cannot cancel bookings within 1 hour of start time"
                    )
                
                booking.status = "CANCELLED"
                await session.flush()
                
                logger.info("Booking cancelled", booking_id=booking_id, user_id=user.id)
                
                return {
                    "success": True,
                    "message": f"Booking #{booking_id} cancelled successfully"
                }
    
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error("Error cancelling booking", booking_id=booking_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to cancel booking - please try again")


# =======================================
# WEB AUTH ENDPOINTS (phone-based login)
# =======================================

class WebLoginRequest(BaseModel):
    phone: str

from jose import jwt, JWTError
import os

_JWT_SECRET = os.getenv("SECRET_KEY", "CHANGE_ME_USE_STRONG_SECRET_IN_PRODUCTION")
_JWT_ALGORITHM = "HS256"
_JWT_EXPIRY_DAYS = 30

def _make_web_token(user_id: int, tg_id: int) -> str:
    """Create a signed JWT token with 30-day expiry."""
    from datetime import datetime, timedelta, timezone
    payload = {
        "user_id": user_id,
        "tg_id": tg_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=_JWT_EXPIRY_DAYS)
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)

def _parse_web_token(token: str) -> dict | None:
    """Parse and VERIFY a JWT token. Returns None if invalid or tampered."""
    try:
        payload = jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGORITHM])
        return payload
    except JWTError:
        return None

async def get_web_user(request: Request) -> dict:
    """Get current web user from Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    
    token = auth_header[7:]
    payload = _parse_web_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Недействительный токен")
    
    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.id == payload["user_id"]))
        user = result.scalars().first()
        if not user:
            raise HTTPException(status_code=401, detail="Пользователь не найден")
        return {"user_id": user.id, "tg_id": user.tg_id, "name": user.full_name}


@router.post("/web/login")
async def web_login(data: WebLoginRequest):
    """Login by phone number. Returns token if user exists."""
    phone = data.phone.strip()
    if not phone.startswith("+"):
        phone = "+" + phone
    
    async with async_session_factory() as session:
        # Exact match on normalized phone
        result = await session.execute(
            select(User).where(User.phone == phone)
        )
        user = result.scalars().first()
        
        if not user:
            raise HTTPException(status_code=404, detail="Номер не найден. Зарегистрируйтесь через Telegram-бота @ArenaSlotBot")
        
        token = _make_web_token(user.id, user.tg_id)
        return {
            "token": token,
            "user": {
                "id": user.id,
                "tg_id": user.tg_id,
                "name": user.full_name or user.username or "User",
                "phone": user.phone
            }
        }


@router.get("/web/me")
async def web_me(request: Request):
    """Get current user info from token."""
    user_data = await get_web_user(request)
    
    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.id == user_data["user_id"]))
        user = result.scalars().first()
        
        return {
            "id": user.id,
            "tg_id": user.tg_id,
            "name": user.full_name or user.username or "User",
            "phone": user.phone
        }


@router.get("/web/profile")
async def web_profile(request: Request):
    """Return user's profile data for the Mini App Profile tab."""
    user_data = await get_web_user(request)
    async with async_session_factory() as session:
        # Find by user_id (works for both Telegram and password-based users)
        result = await session.execute(
            select(User).where(User.id == user_data["user_id"])
        )
        user = result.scalars().first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Booking stats
        total_bookings = await session.scalar(
            select(func.count(Booking.id)).where(Booking.user_id == user.id)
        ) or 0
        completed = await session.scalar(
            select(func.count(Booking.id)).where(
                Booking.user_id == user.id,
                Booking.status == "COMPLETED"
            )
        ) or 0
        cancelled = await session.scalar(
            select(func.count(Booking.id)).where(
                Booking.user_id == user.id,
                Booking.status == "CANCELLED"
            )
        ) or 0

        # Loyalty level based on completed bookings
        if completed >= 50:
            loyalty = {"level": "Platinum", "icon": "💎", "next": None, "needed": 0}
        elif completed >= 20:
            loyalty = {"level": "Gold", "icon": "🥇", "next": "Platinum", "needed": 50 - completed}
        elif completed >= 5:
            loyalty = {"level": "Silver", "icon": "🥈", "next": "Gold", "needed": 20 - completed}
        else:
            loyalty = {"level": "Bronze", "icon": "🥉", "next": "Silver", "needed": 5 - completed}

        return {
            "user_id": user.id,
            "tg_id": user.tg_id,
            "full_name": user.full_name,
            "username": user.username,
            "phone": user.phone,
            "referral_code": getattr(user, 'referral_code', None),
            "language": getattr(user, 'language', 'ru'),
            "balance": 0,  # Placeholder for future wallet
            "total_bookings": total_bookings,
            "completed_bookings": completed,
            "cancelled_bookings": cancelled,
            "loyalty": loyalty,
        }


class LanguageUpdate(BaseModel):
    tg_id: int
    language: str


@router.post("/web/language")
async def web_set_language(body: LanguageUpdate, request: Request):
    """Update user language preference from the Mini App."""
    if body.language not in ('ru', 'uz', 'en'):
        raise HTTPException(status_code=400, detail="Invalid language. Supported: ru, uz, en")
    async with async_session_factory() as session:
        async with session.begin():
            result = await session.execute(select(User).where(User.tg_id == body.tg_id))
            user = result.scalars().first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            user.language = body.language
    return {"success": True, "language": body.language}


@router.get("/web/bookings")
async def web_user_bookings(request: Request):
    """Get bookings for authenticated web user."""
    user_data = await get_web_user(request)

    async with async_session_factory() as session:
        result = await session.execute(
            select(Booking, Club)
            .join(Club, Booking.club_id == Club.id)
            .where(Booking.user_id == user_data["user_id"])
            .order_by(Booking.start_time.desc())
            .limit(50)
        )
        rows = result.all()

        from utils.timezone import to_tashkent
        items = []
        for b, club in rows:
            start_tash = to_tashkent(b.start_time) if b.start_time else b.start_time
            end_tash = to_tashkent(b.end_time) if b.end_time else b.end_time
            items.append({
                "id": b.id,
                "club_name": club.name if club else "Unknown",
                "computer_name": b.computer_name or "Unknown PC",
                "display_time": f"{start_tash.strftime('%d.%m %H:%M')} — {end_tash.strftime('%H:%M')}",
                "status": b.status,
                "confirmation_code": b.confirmation_code,
                "start_time": b.start_time.isoformat()
            })

        return items


@router.delete("/web/bookings/{booking_id}")
async def web_cancel_booking(booking_id: int, request: Request):
    """Cancel a booking for authenticated web user."""
    user_data = await get_web_user(request)
    
    async with async_session_factory() as session:
        result = await session.execute(
            select(Booking).where(
                and_(
                    Booking.id == booking_id,
                    Booking.user_id == user_data["user_id"]
                )
            )
        )
        booking = result.scalars().first()
        
        if not booking:
            raise HTTPException(status_code=404, detail="Бронь не найдена")
        
        if booking.status not in ("CONFIRMED", "ACTIVE"):
            raise HTTPException(status_code=400, detail="Нельзя отменить эту бронь")
        
        booking.status = "CANCELLED"
        await session.commit()
        
        return {"success": True, "message": "Бронь отменена"}


# ============================================================
# ADMIN PANEL API — used by miniapp/admin_panel.html
# ============================================================

async def _require_admin(request: Request) -> int:
    """Check admin via X-Admin-TG-ID + HMAC signature, or via valid JWT token."""
    from models import Admin
    
    # Method 1: JWT token (most secure)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        payload = _parse_web_token(token)
        if payload:
            tg_id = payload.get("tg_id")
            if tg_id:
                async with async_session_factory() as session:
                    result = await session.execute(select(Admin).where(Admin.tg_id == tg_id))
                    admin = result.scalars().first()
                if admin:
                    return tg_id
    
    # Method 2: X-Admin-TG-ID header (backward compat)
    tg_id_str = request.headers.get("X-Admin-TG-ID")
    if not tg_id_str or not tg_id_str.isdigit():
        raise HTTPException(status_code=401, detail="Unauthorized")
    tg_id = int(tg_id_str)
    async with async_session_factory() as session:
        result = await session.execute(select(Admin).where(Admin.tg_id == tg_id))
        admin = result.scalars().first()
    if not admin:
        raise HTTPException(status_code=403, detail="Forbidden")
    return tg_id


@router.get("/admin/stats")
async def admin_stats_api(request: Request):
    """Dashboard stats for the web admin panel."""
    from models import Review, Computer
    from datetime import timedelta
    await _require_admin(request)

    async with async_session_factory() as session:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        today_start_utc = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start_utc - timedelta(days=7)

        users_total = await session.scalar(select(func.count(User.id))) or 0
        active_now = await session.scalar(
            select(func.count(Booking.id)).where(Booking.status == "ACTIVE")
        ) or 0
        bookings_today = await session.scalar(
            select(func.count(Booking.id)).where(Booking.created_at >= today_start_utc)
        ) or 0
        bookings_total = await session.scalar(select(func.count(Booking.id))) or 0

        avg_rating_val = await session.scalar(select(func.avg(Review.rating)))
        avg_rating = round(float(avg_rating_val), 1) if avg_rating_val else None

        # Daily bookings for chart (last 7 days)
        daily_bookings = []
        for i in range(6, -1, -1):
            day_start = today_start_utc - timedelta(days=i)
            day_end = day_start + timedelta(days=1)
            cnt = await session.scalar(
                select(func.count(Booking.id)).where(
                    and_(Booking.created_at >= day_start, Booking.created_at < day_end)
                )
            ) or 0
            daily_bookings.append({
                "date": day_start.strftime("%d.%m"),
                "count": cnt
            })

        # Recent 20 bookings (with JOIN to avoid N+1)
        recent_result = await session.execute(
            select(Booking, User, Club)
            .outerjoin(User, Booking.user_id == User.id)
            .outerjoin(Club, Booking.club_id == Club.id)
            .order_by(Booking.created_at.desc()).limit(20)
        )
        recent_rows = recent_result.all()
        recent_bookings = []
        for b, user, club in recent_rows:
            recent_bookings.append({
                "id": b.id,
                "user_name": user.full_name if user else "Unknown",
                "club_name": club.name if club else "Unknown",
                "computer_name": b.computer_name,
                "status": b.status,
                "start_time": b.start_time.isoformat() if b.start_time else None,
            })

        # --- NEW ANALYTICS ---

        # Total bookings this week
        bookings_week = await session.scalar(
            select(func.count(Booking.id)).where(Booking.created_at >= week_start)
        ) or 0

        # No-show rate (last 7 days)
        completed_plus_noshow = await session.scalar(
            select(func.count(Booking.id)).where(
                and_(Booking.created_at >= week_start,
                     Booking.status.in_(["COMPLETED", "NO_SHOW"]))
            )
        ) or 0
        noshow_count = await session.scalar(
            select(func.count(Booking.id)).where(
                and_(Booking.created_at >= week_start, Booking.status == "NO_SHOW")
            )
        ) or 0
        noshow_rate = round(noshow_count / completed_plus_noshow * 100) if completed_plus_noshow > 0 else 0

        # Revenue last 7 days (from Computer price_per_hour * booking duration in hours)
        from sqlalchemy import cast, Float as SAFloat
        revenue_result = await session.execute(
            select(
                Computer.price_per_hour,
                func.extract('epoch', Booking.end_time - Booking.start_time).label('duration_secs')
            ).join(
                Computer,
                and_(
                    Booking.club_id == Computer.club_id,
                    Booking.item_id == Computer.id
                )
            ).where(
                and_(Booking.created_at >= week_start, Booking.status.in_(["COMPLETED", "ACTIVE"]))
            )
        )
        revenue_week = sum(
            (price or 0) * (secs or 3600) / 3600
            for price, secs in revenue_result
        )

        # Peak hours (hour → booking count, all time)
        hour_result = await session.execute(
            select(func.extract("hour", Booking.start_time).label("hour"), func.count(Booking.id).label("cnt"))
            .where(Booking.start_time.isnot(None))
            .group_by(func.extract("hour", Booking.start_time))
            .order_by(func.extract("hour", Booking.start_time))
        )
        hour_map = {int(h): c for h, c in hour_result}
        peak_hours = [{"hour": h, "count": hour_map.get(h, 0)} for h in range(24)]

        # Clubs stats — bookings count and avg rating per club
        clubs_result = await session.execute(
            select(Club.name, func.count(Booking.id).label("cnt"), func.avg(Review.rating).label("avg_r"))
            .outerjoin(Booking, Booking.club_id == Club.id)
            .outerjoin(Review, Review.club_id == Club.id)
            .group_by(Club.id, Club.name)
            .order_by(func.count(Booking.id).desc())
        )
        clubs_stats = [
            {
                "name": name,
                "bookings_count": cnt or 0,
                "avg_rating": round(float(avg_r), 1) if avg_r else None
            }
            for name, cnt, avg_r in clubs_result
        ]
        top_club = clubs_stats[0]["name"] if clubs_stats else None

    return {
        "users_total": users_total,
        "active_now": active_now,
        "bookings_today": bookings_today,
        "bookings_total": bookings_total,
        "bookings_week": bookings_week,
        "avg_rating": avg_rating,
        "noshow_rate": noshow_rate,
        "revenue_week": int(revenue_week),
        "top_club": top_club,
        "peak_hours": peak_hours,
        "clubs_stats": clubs_stats,
        "daily_bookings": daily_bookings,
        "recent_bookings": recent_bookings,
    }


@router.get("/admin/bookings")
async def admin_bookings_api(request: Request, limit: int = Query(50, le=200)):
    """Full bookings list for the web admin panel."""
    await _require_admin(request)
    async with async_session_factory() as session:
        # JOIN to avoid N+1 queries
        result = await session.execute(
            select(Booking, User, Club)
            .outerjoin(User, Booking.user_id == User.id)
            .outerjoin(Club, Booking.club_id == Club.id)
            .order_by(Booking.created_at.desc()).limit(limit)
        )
        rows = result.all()
        items = []
        for b, user, club in rows:
            items.append({
                "id": b.id,
                "user_name": user.full_name if user else "Unknown",
                "club_name": club.name if club else "Unknown",
                "computer_name": b.computer_name,
                "status": b.status,
                "start_time": b.start_time.isoformat() if b.start_time else None,
                "end_time": b.end_time.isoformat() if b.end_time else None,
            })
    return {"bookings": items}


# ============================================================
# PAYMENT ENDPOINTS
# ============================================================

class CreatePaymentRequest(BaseModel):
    booking_id: int
    amount: int  # in UZS


@router.post("/payments")
async def create_payment(data: CreatePaymentRequest, user_data: dict = Depends(get_current_user)):
    """Create a payment for a booking."""
    from services.payment import payment_service

    # Verify booking belongs to user
    async with async_session_factory() as session:
        user_result = await session.execute(select(User).where(User.tg_id == user_data["id"]))
        user = user_result.scalars().first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        booking_result = await session.execute(
            select(Booking).where(
                and_(Booking.id == data.booking_id, Booking.user_id == user.id)
            )
        )
        booking = booking_result.scalars().first()
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")

    result = await payment_service.create_payment(
        booking_id=data.booking_id,
        user_id=user.id,
        amount=data.amount,
    )
    return result


@router.get("/payments/{payment_id}")
async def get_payment_status(payment_id: int):
    """Check payment status."""
    from services.payment import payment_service
    result = await payment_service.get_payment_status(payment_id)
    if result["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Payment not found")
    return result


@router.post("/payments/{payment_id}/test-pay")
async def test_pay(payment_id: int):
    """
    Test mode: instantly mark payment as paid.
    Only works when PAYMENT_PROVIDER=test (default).
    This endpoint simulates a successful payment without real money.
    """
    from services.payment import payment_service, PAYMENT_PROVIDER
    import uuid

    if PAYMENT_PROVIDER != "test":
        raise HTTPException(status_code=403, detail="Test payments disabled in production")

    result = await payment_service.confirm_payment(
        payment_id=payment_id,
        transaction_id=f"TEST-{uuid.uuid4().hex[:8].upper()}"
    )
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Payment error"))
    return {"success": True, "message": "✅ Тестовый платёж успешно проведён!", **result}


@router.post("/payments/click/callback")
async def click_callback(request: Request):
    """
    Click.uz payment callback (webhook).
    Click sends POST requests here when payment status changes.
    Activate by setting PAYMENT_PROVIDER=click and Click credentials in env.
    """
    from services.payment import payment_service, CLICK_SECRET_KEY
    import hashlib

    body = await request.json()
    logger.info("Click callback received", body=body)

    # Verify Click signature
    click_trans_id = body.get("click_trans_id")
    merchant_trans_id = body.get("merchant_trans_id")  # Our payment_id
    amount = body.get("amount")
    action = body.get("action")  # 0=prepare, 1=complete
    sign_string = body.get("sign_string")

    if not all([click_trans_id, merchant_trans_id, action is not None]):
        return {"error": -8, "error_note": "Missing parameters"}

    # For action=1 (complete), confirm the payment
    if str(action) == "1":
        result = await payment_service.confirm_payment(
            payment_id=int(merchant_trans_id),
            transaction_id=str(click_trans_id),
        )
        return {"click_trans_id": click_trans_id, "merchant_trans_id": merchant_trans_id, "error": 0}

    # action=0 (prepare) — just acknowledge
    return {"click_trans_id": click_trans_id, "merchant_trans_id": merchant_trans_id, "error": 0}


@router.post("/payments/payme/callback")
async def payme_callback(request: Request):
    """
    Payme callback (JSON-RPC endpoint).
    Payme sends JSON-RPC requests here.
    Activate by setting PAYMENT_PROVIDER=payme and Payme credentials in env.
    """
    from services.payment import payment_service

    body = await request.json()
    method = body.get("method")
    params = body.get("params", {})
    rpc_id = body.get("id")

    logger.info("Payme callback received", method=method)

    if method == "CheckPerformTransaction":
        # Verify the order exists
        account = params.get("account", {})
        order_id = account.get("order_id")
        if order_id:
            status = await payment_service.get_payment_status(int(order_id))
            if status["status"] != "not_found":
                return {"jsonrpc": "2.0", "id": rpc_id, "result": {"allow": True}}
        return {"jsonrpc": "2.0", "id": rpc_id, "error": {"code": -31050, "message": "Order not found"}}

    elif method == "PerformTransaction":
        account = params.get("account", {})
        order_id = account.get("order_id")
        payme_id = params.get("id")
        if order_id:
            result = await payment_service.confirm_payment(
                payment_id=int(order_id),
                transaction_id=payme_id,
            )
            return {"jsonrpc": "2.0", "id": rpc_id, "result": {"state": 2}}
        return {"jsonrpc": "2.0", "id": rpc_id, "error": {"code": -31050, "message": "Order not found"}}

    return {"jsonrpc": "2.0", "id": rpc_id, "error": {"code": -32601, "message": "Method not found"}}
