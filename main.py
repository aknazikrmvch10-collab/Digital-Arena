import asyncio
import logging
import os
import sys
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message
from aiogram.filters import CommandStart
from sqlalchemy import select

from config import settings as settings_config
from database import init_db, async_session_factory
from seed_data import seed_test_clubs
from aiogram.types import BotCommand
from utils.limiter import limiter
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from utils.logging import configure_structlog, get_logger
from keyboards.main import get_main_menu, get_main_reply_keyboard

# Configure logging
configure_structlog()
logger = get_logger(__name__)

# FastAPI imports
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from handlers.api import router as api_router
import uvicorn
from models import User

# Import handlers
# Handlers are imported below (line 153) — removed duplicate import here

# Initialize Bot
bot = Bot(token=settings_config.BOT_TOKEN)

# FastAPI application
fastapi_app = FastAPI()
fastapi_app.state.limiter = limiter
fastapi_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS Middleware
# ✅ FIX #2: allow_origins=["*"] + allow_credentials=True is forbidden by CORS spec
# Use specific origins instead
from fastapi.middleware.cors import CORSMiddleware
import os as _os
_ALLOWED_ORIGINS = _os.getenv("ALLOWED_ORIGINS", "").split(",")
# Always include known frontend origins
_ALLOWED_ORIGINS = [o.strip() for o in _ALLOWED_ORIGINS if o.strip()] or [
    "https://arenaslotz.web.app",
    "https://arenaslotz.firebaseapp.com",
    "http://localhost:3000",
    "http://localhost:8000",
]
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
fastapi_app.include_router(api_router, prefix="/api")
fastapi_app.mount("/website", StaticFiles(directory="website", html=True), name="website")
fastapi_app.mount("/miniapp", StaticFiles(directory="miniapp", html=True), name="miniapp")
fastapi_app.mount("/", StaticFiles(directory="public", html=True), name="public")
dp = Dispatcher()

# Create start router
start_router = Router()

@start_router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    # Check for deep link parameter (e.g., book_{club_id})
    args = message.text.split(maxsplit=1)
    deep_link = args[1] if len(args) > 1 else None
    
    # Register user if not exists
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
            except Exception as e:
                logger.warning(f"Error creating user {message.from_user.id}: {str(e)}")
                # User might have been created by a parallel request
                await session.rollback()
                result = await session.execute(select(User).where(User.tg_id == message.from_user.id))
                user = result.scalars().first()
        
        # Check if age is confirmed
        if not user.age_confirmed:
            # Show age verification
            age_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Мне есть 18 лет", callback_data="confirm_age_18")]
            ])
            
            await message.answer(
                f"👋 <b>Добро пожаловать, {message.from_user.full_name}!</b>\n\n"
                "⚠️ <b>Важное уведомление:</b>\n\n"
                "Согласно законодательству Республики Узбекистан, услуги компьютерных клубов "
                "предоставляются лицам, достигшим 18 лет.\n\n"
                "Используя данного бота, вы подтверждаете, что вам исполнилось 18 лет.",
                reply_markup=age_keyboard,
                parse_mode="HTML"
            )
        else:
            # Check if user came from website with deep link
            if deep_link and deep_link.startswith("book_"):
                try:
                    club_id = int(deep_link.split("_")[1])
                    await message.answer(
                        f"👋 <b>С возвращением, {message.from_user.full_name}!</b>\n\n"
                        "Нажмите «🏢 Клубы» чтобы выбрать клуб и забронировать место!",
                        reply_markup=get_main_reply_keyboard(),
                        parse_mode="HTML"
                    )
                    return
                except (ValueError, IndexError):
                    pass  # Invalid parameter, show normal menu
            
            # Check if phone is missing — prompt immediately!
            if not user.phone:
                from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
                phone_keyboard = ReplyKeyboardMarkup(
                    keyboard=[
                        [KeyboardButton(text="📱 Отправить номер телефона", request_contact=True)],
                        [KeyboardButton(text="⏩ Пропустить")]
                    ],
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
            
            # Show main menu for verified users with phone
            await message.answer(
                f"👋 <b>С возвращением, {message.from_user.full_name}!</b>\n\n"
                "Я — Универсальный бот для бронирования компьютерных клубов Узбекистана.\n"
                "Находите и бронируйте компьютеры в любом клубе через меня!",
                reply_markup=get_main_reply_keyboard(),
                parse_mode="HTML"
            )

# Import handlers
from handlers import clubs, settings, age_verification, filters, admin, webapp, users
from handlers import referral, reviews
from handlers import language, promo, broadcast, club_settings


# Register routers
dp.include_router(admin.router) # Admin router first
dp.include_router(webapp.router) # Web App data handler
dp.include_router(age_verification.router)
dp.include_router(filters.router)
dp.include_router(clubs.router)
dp.include_router(settings.router)
dp.include_router(users.router) # User profile & bookings
dp.include_router(reviews.router) # Review callbacks
dp.include_router(referral.router) # Referral /referral command
dp.include_router(language.router) # Language /language command
dp.include_router(promo.router) # Promo codes /promo command
dp.include_router(broadcast.router) # Admin broadcast
dp.include_router(club_settings.router) # Club settings FSM
dp.include_router(start_router)

async def main():
    """Main bot startup."""
    # Initialize database
    await init_db()
    
    # Initialize Redis cache (graceful - won't crash if Redis unavailable)
    from services.redis_client import cache
    await cache.connect()
    
    # Seed test data
    await seed_test_clubs()
    
    # Start background tasks
    from background_tasks import (
        check_no_show_bookings, check_activate_bookings,
        check_auto_complete_bookings, send_reminder_notifications, send_review_requests
    )
    asyncio.create_task(check_no_show_bookings())
    asyncio.create_task(check_activate_bookings())   # CONFIRMED → ACTIVE
    asyncio.create_task(check_auto_complete_bookings())
    asyncio.create_task(send_reminder_notifications(bot))
    asyncio.create_task(send_review_requests(bot))

    # Start FastAPI server in background
    async def start_server():
        port = int(os.getenv("PORT", 8000))
        config = uvicorn.Config(fastapi_app, host="0.0.0.0", port=port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()
    
    asyncio.create_task(start_server())
    
    logger.info("Bot is starting...")
    
    # Set bot commands
    from aiogram.types import BotCommand
    await bot.set_my_commands([
        BotCommand(command="start", description="🔄 Перезапустить бота"),
        BotCommand(command="help", description="🆘 Помощь"),
        BotCommand(command="profile", description="👤 Мой профиль"),
        BotCommand(command="phone", description="📱 Указать номер телефона"),
        BotCommand(command="referral", description="🎁 Реферальная программа"),
        BotCommand(command="promo", description="🎫 Ввести промокод"),
        BotCommand(command="language", description="🌍 Изменить язык"),
        BotCommand(command="admin", description="🔐 Админ-панель")
    ])
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    # Safety warning when running locally (not on Render)
    if not os.getenv("RENDER"):
        print("\n[WARNING] If the bot is already running on Render 24/7,")
        print("   running locally will cause a TelegramConflictError.")
        print("   Use a DIFFERENT token in .env for local development.\n")
    asyncio.run(main())
