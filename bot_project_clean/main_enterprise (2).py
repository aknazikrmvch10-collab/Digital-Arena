"""
🚀 Enterprise-grade Digital Arena Bot
Advanced architecture with monitoring, security, and resilience features.
"""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message, BotCommand
from aiogram.filters import CommandStart
from sqlalchemy import select

# Enterprise imports
from config import settings as settings_config
from database import init_db, async_session_factory
from seed_data import seed_test_clubs
from utils.logging import configure_structlog, get_logger
from utils.monitoring import (
    metrics_collector, system_monitor, performance_profiler, 
    alert_manager, metrics_collector
)
from utils.security import security_manager
from utils.circuit_breaker import ICAFE_BREAKER, REDIS_BREAKER, DATABASE_BREAKER
from utils.advanced_cache import advanced_cache
from utils.event_bus import event_bus, BookingCreatedEvent, UserRegisteredEvent
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import uvicorn

# Configure enterprise logging
configure_structlog()
logger = get_logger(__name__)

# Prometheus Metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')
ACTIVE_CONNECTIONS = Gauge('active_connections', 'Active connections')
BOOKINGS_CREATED = Counter('bookings_created_total', 'Total bookings created')
USERS_REGISTERED = Counter('users_registered_total', 'Total users registered')

# FastAPI application with enterprise features
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Enterprise application lifespan management."""
    logger.info("🚀 Starting Digital Arena Enterprise Edition...")
    
    # Initialize database with circuit breaker
    try:
        await DATABASE_BREAKER._call_async(init_db)
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise
    
    # Initialize Redis cache with circuit breaker
    try:
        from services.redis_client import cache
        await REDIS_BREAKER._call_async(cache.connect)
        logger.info("✅ Redis cache initialized successfully")
    except Exception as e:
        logger.warning(f"⚠️ Redis initialization failed: {e}")
    
    # Start system monitoring
    await system_monitor.start_monitoring(interval=30.0)
    logger.info("📊 System monitoring started")
    
    # Seed test data
    await seed_test_clubs()
    logger.info("🌱 Test data seeded")
    
    # Start background tasks
    from background_tasks import (
        check_no_show_bookings, 
        check_auto_complete_bookings, 
        send_reminder_notifications
    )
    
    asyncio.create_task(check_no_show_bookings())
    asyncio.create_task(check_auto_complete_bookings())
    asyncio.create_task(send_reminder_notifications(bot))
    logger.info("🔄 Background tasks started")
    
    # Cache warmup
    await advanced_cache.warmup({
        "clubs": lambda: get_clubs_data(),
        "computers": lambda: get_computers_data()
    })
    logger.info("🔥 Cache warmed up")
    
    yield
    
    # Cleanup
    await system_monitor.stop_monitoring()
    logger.info("🛑 System monitoring stopped")

fastapi_app = FastAPI(
    title="Digital Arena Enterprise API",
    description="Enterprise-grade booking platform for computer clubs",
    version="2.0.0",
    lifespan=lifespan
)

# Enterprise middleware
@fastapi_app.middleware("http")
@performance_profiler.profile("http_request")
async def enterprise_middleware(request: Request, call_next):
    """Enterprise middleware with security, monitoring, and rate limiting."""
    
    # Security context
    security_context = security_manager.create_security_context(request)
    
    # Rate limiting
    if not security_manager.rate_limiter.is_allowed(security_context.ip_address):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # IP filtering
    if not security_manager.ip_filter.is_allowed(security_context.ip_address):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Metrics
    start_time = time.time()
    ACTIVE_CONNECTIONS.inc()
    
    try:
        response = await call_next(request)
        
        # Record metrics
        duration = time.time() - start_time
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()
        REQUEST_DURATION.observe(duration)
        
        return response
    
    except Exception as e:
        # Record error metrics
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=500
        ).inc()
        
        logger.error(f"Request failed: {e}")
        raise
    
    finally:
        ACTIVE_CONNECTIONS.dec()

# CORS with enterprise configuration
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=settings_config.ALLOWED_ORIGINS.split(",") if settings_config.ALLOWED_ORIGINS else [
        "https://arenaslotz.web.app",
        "https://arenaslotz.firebaseapp.com",
        "http://localhost:3000",
        "http://localhost:8000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Metrics endpoint
@fastapi_app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(generate_latest(), media_type="text/plain")

# Health check with enterprise features
@fastapi_app.get("/api/health")
async def health_check():
    """Enterprise health check with detailed status."""
    import time
    start_time = time.time()
    
    health = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0",
        "services": {},
        "metrics": metrics_collector.get_stats(),
        "circuit_breakers": {
            "icafe": ICAFE_BREAKER.get_state(),
            "redis": REDIS_BREAKER.get_state(),
            "database": DATABASE_BREAKER.get_state()
        }
    }
    
    # Check Database
    try:
        async with async_session_factory() as session:
            await session.execute(select(1))
        health["services"]["database"] = {"status": "ok", "response_time_ms": round((time.time() - start_time) * 1000, 2)}
    except Exception as e:
        health["services"]["database"] = {"status": "error", "detail": str(e)}
        health["status"] = "degraded"
    
    # Check Redis
    try:
        from services.redis_client import cache
        await cache.ping()
        health["services"]["redis"] = {"status": "ok"}
    except Exception as e:
        health["services"]["redis"] = {"status": "error", "detail": str(e)}
        health["status"] = "degraded"
    
    # Check alerts
    alerts = await alert_manager.check_alerts()
    if alerts:
        health["alerts"] = alerts
        if any(alert["severity"] == "critical" for alert in alerts):
            health["status"] = "critical"
    
    health["response_time_ms"] = round((time.time() - start_time) * 1000, 2)
    
    # Return appropriate status code
    status_code = 200 if health["status"] == "healthy" else 503
    
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=status_code, content=health)

# Mount static files
fastapi_app.mount("/website", StaticFiles(directory="website", html=True), name="website")
fastapi_app.mount("/miniapp", StaticFiles(directory="miniapp", html=True), name="miniapp")
fastapi_app.mount("/", StaticFiles(directory="public", html=True), name="public")

# Include API routes
from handlers.api import router as api_router
fastapi_app.include_router(api_router, prefix="/api")

# Initialize Bot
bot = Bot(token=settings_config.BOT_TOKEN)
dp = Dispatcher()

# Create start router with enterprise features
start_router = Router()

@start_router.message(CommandStart())
@performance_profiler.profile("start_command")
async def command_start_handler(message: Message) -> None:
    """Enhanced start handler with enterprise features."""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    # Security context
    security_context = security_manager.create_security_context(message)
    
    # Rate limiting check
    if not security_manager.rate_limiter.is_allowed(f"tg:{message.from_user.id}"):
        await message.answer("⚠️ Too many requests. Please try again later.")
        return
    
    args = message.text.split(maxsplit=1)
    deep_link = args[1] if len(args) > 1 else None
    
    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.tg_id == message.from_user.id))
        user = result.scalars().first()
        
        if not user:
            try:
                user = User(
                    tg_id=message.from_user.id,
                    username=message.from_user.username,
                    full_name=message.from_user.full_name
                )
                session.add(user)
                await session.commit()
                await session.refresh(user)
                
                # Publish user registration event
                await event_bus.publish(UserRegisteredEvent({
                    "user_id": user.id,
                    "tg_id": user.tg_id,
                    "username": user.username,
                    "full_name": user.full_name,
                    "security_context": security_context.__dict__
                }))
                
                USERS_REGISTERED.inc()
                logger.info(f"New user registered: {user.tg_id}")
                
            except Exception as e:
                await session.rollback()
                logger.error(f"User registration failed: {e}")
                result = await session.execute(select(User).where(User.tg_id == message.from_user.id))
                user = result.scalars().first()
        
        # Age verification check
        if not user.age_confirmed:
            age_keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="✅ Мне есть 18 лет", callback_data="confirm_age_18")
            ]])
            
            await message.answer(
                f"👋 <b>Добро пожаловать, {message.from_user.full_name}!</b>\n\n"
                "⚠️ <b>Важное уведомление:</b>\n\n"
                "Согласно законодательству Республики Узбекистан, услуги компьютерных клубов "
                "предоставляются лицам, достигшим 18 лет.\n\n"
                "Используя данного бота, вы подтверждаете, что вам исполнилось 18 лет.",
                reply_markup=age_keyboard,
                parse_mode="HTML"
            )
            return
        
        # Phone verification check
        if not user.phone:
            from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
            phone_keyboard = ReplyKeyboardMarkup(
                keyboard=[[
                    KeyboardButton(text="📱 Отправить номер телефона", request_contact=True),
                    KeyboardButton(text="⏩ Пропустить")
                ]],
                resize_keyboard=True,
                one_time_keyboard=True
            )
            await message.answer(
                f"👋 <b>Добро пожаловать, {message.from_user.full_name}!</b>\n\n"
                "📱 <b>Укажите номер телефона</b>, чтобы:\n"
                "• Входить на <b>сайт</b> Digital Arena\n"
                "• Получать уведомления о бронях\n"
                "• Связь с администратором клуба\n\n"
                "👇 <b>Нажмите кнопку ниже:</b>",
                reply_markup=phone_keyboard,
                parse_mode="HTML"
            )
            return
        
        # Show main menu
        from keyboards.main import get_main_reply_keyboard
        await message.answer(
            f"👋 <b>С возвращением, {message.from_user.full_name}!</b>\n\n"
            "🚀 <b>Digital Arena Enterprise Edition</b>\n"
            "Я — Универсальный бот для бронирования компьютерных клубов Узбекистана.\n"
            "Находите и бронируйте компьютеры в любом клубе через меня!",
            reply_markup=get_main_reply_keyboard(),
            parse_mode="HTML"
        )

# Import and register handlers
from handlers import clubs, settings, age_verification, filters, admin, webapp, users

dp.include_router(admin.router)
dp.include_router(webapp.router)
dp.include_router(age_verification.router)
dp.include_router(filters.router)
dp.include_router(clubs.router)
dp.include_router(settings.router)
dp.include_router(users.router)
dp.include_router(start_router)

async def main():
    """Main enterprise bot startup."""
    logger.info("🚀 Starting Digital Arena Enterprise Bot...")
    
    # Start FastAPI server in background
    async def start_server():
        port = int(os.getenv("PORT", 8000))
        config = uvicorn.Config(
            fastapi_app, 
            host="0.0.0.0", 
            port=port, 
            log_level="info",
            access_log=True
        )
        server = uvicorn.Server(config)
        await server.serve()
    
    # Start server
    server_task = asyncio.create_task(start_server())
    logger.info("🌐 FastAPI server started")
    
    # Set bot commands
    await bot.set_my_commands([
        BotCommand(command="start", description="🔄 Перезапустить бота"),
        BotCommand(command="help", description="🆘 Помощь"),
        BotCommand(command="profile", description="👤 Мой профиль"),
        BotCommand(command="phone", description="📱 Указать номер телефона"),
        BotCommand(command="admin", description="🔐 Админ-панель"),
        BotCommand(command="status", description="📊 Статус системы"),
        BotCommand(command="metrics", description="📈 Метрики")
    ])
    
    logger.info("🤖 Bot commands configured")
    
    # Start bot polling
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Bot polling failed: {e}")
        raise
    finally:
        server_task.cancel()

if __name__ == "__main__":
    # Safety warning
    if not os.getenv("RENDER"):
        print("\n[WARNING] If the bot is already running on Render 24/7,")
        print("   running locally will cause a TelegramConflictError.")
        print("   Use a DIFFERENT token in .env for local development.\n")
    
    asyncio.run(main())
