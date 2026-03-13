import asyncio
import logging
import sys
import os
from os import getenv

import aiogram
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command, CommandStart
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import init_db, async_session_factory
from seed_data import seed_test_clubs
from aiogram.types import BotCommand
from utils.limiter import limiter
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from utils.logging import get_logger
from keyboards.main import get_main_reply_keyboard
from i18n import t

import sentry_sdk
if settings.SENTRY_DSN:
    sentry_sdk.init(dsn=settings.SENTRY_DSN, traces_sample_rate=1.0)

# Init Logger
logger = get_logger(__name__)

# Verify Bot Token
TOKEN = settings.BOT_TOKEN
if not TOKEN or ":" not in TOKEN:
    logger.error("BOT_TOKEN is missing or invalid! Please check your .env file.")
    sys.exit(1)

# Initialize Bot and Dispatcher
bot = Bot(token=TOKEN)

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from handlers.api import api_router
from handlers.audit import audit_router
from handlers.gov import gov_router
from handlers.club_admin import club_admin_router
import uvicorn
from models import User, Booking, Club, Admin
from fastapi.middleware.cors import CORSMiddleware

fastapi_app = FastAPI(title="Digital Arena API")
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

fastapi_app.include_router(api_router, prefix="/api")
fastapi_app.include_router(audit_router, prefix="/api")
fastapi_app.include_router(gov_router, prefix="/api")
fastapi_app.include_router(club_admin_router, prefix="/api")
fastapi_app.mount("/website", StaticFiles(directory="website", html=True), name="website")
fastapi_app.mount("/miniapp", StaticFiles(directory="miniapp", html=True), name="miniapp")
fastapi_app.mount("/", StaticFiles(directory="public", html=True), name="public")

dp = Dispatcher()
start_router = Router()

@start_router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    # Check for deep link parameter (e.g., ref_CODE)
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
                    full_name=message.from_user.full_name,
                    language='ru'
                )
                session.add(user)
                await session.commit()
                await session.refresh(user)
                
                # Process referral if link exists
                if deep_link and deep_link.startswith("ref_"):
                    from handlers.referral import process_referral_on_start
                    await process_referral_on_start(user, deep_link, session)
                    
            except Exception as e:
                logger.warning(f"Error creating user {message.from_user.id}: {str(e)}")
                await session.rollback()
                result = await session.execute(select(User).where(User.tg_id == message.from_user.id))
                user = result.scalars().first()
        
        lang = user.language if user and user.language else 'ru'
        
        if not user.age_confirmed:
            age_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Мне есть 18+ — войти!", callback_data="confirm_age_18")]
            ])
            await message.answer_photo(
                photo="https://i.imgur.com/8Km9tLL.jpeg",
                caption=(
                    f"🎮 <b>Digital Arena</b>\n\n"
                    f"👋 Привет, <b>{message.from_user.full_name}</b>!\n\n"
                    "❌ Доступ ограничен по возрасту. Сервис доступен только лицам старше 18 лет."
                ),
                reply_markup=age_keyboard,
                parse_mode="HTML"
            )
        else:
            if not user.phone:
                phone_keyboard = ReplyKeyboardMarkup(
                    keyboard=[
                        [KeyboardButton(text=t(lang, 'btn_phone_share') if lang=='ru' else "📱 Share Phone", request_contact=True)],
                        [KeyboardButton(text=t(lang, 'btn_skip') if lang=='ru' else "⏩ Skip")]
                    ],
                    resize_keyboard=True, one_time_keyboard=True
                )
                await message.answer(
                    f"📱 {t(lang, 'enter_phone_prompt') if lang=='ru' else 'Please share your phone number to continue:'}",
                    reply_markup=phone_keyboard,
                    parse_mode="HTML"
                )
                return

            reply_markup = get_main_reply_keyboard(lang=lang)
            await message.answer(
                f"🎮 <b>Digital Arena</b>\n\n"
                f"👋 {t(lang, 'start_welcome')}",
                reply_markup=reply_markup,
                parse_mode="HTML"
            )

# Import and Register Handlers
from handlers import clubs, settings, age_verification, filters, admin, webapp, users
from handlers import referral, reviews, language, promo, broadcast, club_settings, app_auth

dp.include_router(admin.router)
dp.include_router(webapp.router)
dp.include_router(age_verification.router)
dp.include_router(filters.router)
dp.include_router(clubs.router)
dp.include_router(settings.router)
dp.include_router(users.router)
dp.include_router(reviews.router)
dp.include_router(referral.router)
dp.include_router(language.router)
dp.include_router(promo.router)
dp.include_router(broadcast.router)
dp.include_router(club_settings.router)
dp.include_router(app_auth.router)
dp.include_router(start_router)

async def main():
    await init_db()
    from services.redis_client import cache
    await cache.connect()
    await seed_test_clubs()
    
    from background_tasks import (
        check_no_show_bookings, check_activate_bookings,
        check_auto_complete_bookings, send_reminder_notifications,
        send_review_requests, cleanup_old_logs, keep_awake
    )
    asyncio.create_task(check_no_show_bookings())
    asyncio.create_task(check_activate_bookings())
    asyncio.create_task(check_auto_complete_bookings())
    asyncio.create_task(send_reminder_notifications(bot))
    asyncio.create_task(send_review_requests(bot))
    asyncio.create_task(cleanup_old_logs())
    asyncio.create_task(keep_awake())

    await bot.set_my_commands([
        BotCommand(command="start", description="🔄 Перезапустить"),
        BotCommand(command="profile", description="👤 Профиль"),
        BotCommand(command="referral", description="🎁 Рефералы"),
        BotCommand(command="language", description="🌍 Язык"),
        BotCommand(command="admin", description="🔐 Админ")
    ])
    
    # Run FastAPI server and Bot Polling together
    port = int(os.getenv("PORT", 8000))
    config = uvicorn.Config(fastapi_app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    
    logger.info(f"Starting API server on port {port} and Bot polling...")
    
    # Use gather to run both tasks concurrently
    await asyncio.gather(
        server.serve(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")
