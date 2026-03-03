"""
PWA Phone+Code Authentication Handler
--------------------------------------
Command: /myapp
1. User sends /myapp
2. Bot asks to share phone number
3. User shares contact
4. Bot generates a 6-digit code, stores it (10 min TTL)
5. Bot sends the code to the user
"""
import random
import string
from datetime import timedelta

from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import Command

from database import async_session_factory
from models import AppAuthCode, User
from utils.timezone import now_tashkent
from utils.logging import get_logger

router = Router()
logger = get_logger(__name__)


def _generate_code() -> str:
    """Generate a random 6-digit numeric code."""
    return str(random.randint(100000, 999999))


@router.message(Command("myapp"))
@router.message(F.text == "📱 Приложение")
async def cmd_myapp(message: Message):
    """
    Handle /myapp command or button — asks the user to share their phone number.
    """
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Поделиться номером телефона", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer(
        "📲 <b>Digital Arena — Приложение</b>\n\n"
        "Чтобы войти в наше приложение с любого устройства,\n"
        "поделитесь своим номером телефона.\n\n"
        "Мы отправим вам <b>код для входа</b> (действует 10 минут).",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.message(F.contact)
async def handle_contact(message: Message):
    """
    Handle shared contact — generate and store auth code, send to user.
    """
    contact = message.contact

    # Ignore if it's someone else's contact
    if contact.user_id != message.from_user.id:
        await message.answer(
            "⚠️ Пожалуйста, поделитесь <b>своим</b> номером телефона.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="HTML"
        )
        return

    phone = contact.phone_number
    if not phone.startswith("+"):
        phone = "+" + phone

    tg_id = message.from_user.id
    code = _generate_code()
    now = now_tashkent()
    expires = now + timedelta(minutes=10)

    async with async_session_factory() as session:
        # Invalidate any existing unused codes for this user
        from sqlalchemy import select, update
        await session.execute(
            update(AppAuthCode)
            .where(AppAuthCode.user_id == tg_id, AppAuthCode.used == False)
            .values(used=True)
        )

        # Create new code
        auth_code = AppAuthCode(
            user_id=tg_id,
            phone=phone,
            code=code,
            expires_at=expires,
        )
        session.add(auth_code)
        await session.commit()

    logger.info("App auth code generated", tg_id=tg_id, phone=phone)

    await message.answer(
        f"✅ <b>Ваш код для входа в приложение:</b>\n\n"
        f"<code>{code}</code>\n\n"
        f"📱 <b>Номер:</b> {phone}\n"
        f"⏰ Код действует <b>10 минут</b>.\n\n"
        f"Откройте приложение и введите:\n"
        f"• Ваш номер телефона: <code>{phone}</code>\n"
        f"• Этот код: <code>{code}</code>",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML"
    )
