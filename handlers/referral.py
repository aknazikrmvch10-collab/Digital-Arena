"""
Referral system handler.
/referral — shows your referral code and invite link
"""
import random
import string
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select, func
from database import async_session_factory
from models import User, Booking

router = Router()


def generate_referral_code(length=6) -> str:
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


async def get_or_create_referral_code(user: User, session) -> str:
    """Get existing referral code or generate a new one."""
    if not user.referral_code:
        # Generate unique code
        while True:
            code = generate_referral_code()
            existing = await session.execute(select(User).where(User.referral_code == code))
            if not existing.scalars().first():
                user.referral_code = code
                await session.commit()
                break
    return user.referral_code


@router.message(Command("referral"))
async def show_referral(message: Message):
    """Show the user's referral code and invite link."""
    tg_id = message.from_user.id

    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        user = result.scalars().first()

        if not user:
            await message.answer("⚠️ Сначала зарегистрируйтесь через /start")
            return

        code = await get_or_create_referral_code(user, session)

        # Count invited users
        invited_count_result = await session.execute(
            select(func.count(User.id)).where(User.referred_by == user.id)
        )
        invited_count = invited_count_result.scalar() or 0

        bot_info = await message.bot.get_me()
        invite_link = f"https://t.me/{bot_info.username}?start=ref_{code}"

        text = (
            f"🎁 <b>Ваша реферальная программа</b>\n\n"
            f"Приглашайте друзей — получайте бонусы!\n\n"
            f"🔑 <b>Ваш код:</b> <code>{code}</code>\n"
            f"🔗 <b>Ваша ссылка:</b>\n{invite_link}\n\n"
            f"👥 <b>Приглашено друзей:</b> {invited_count}\n\n"
            f"<i>✨ Когда ваш друг сделает первую бронь — вы получите 1 час бесплатно!</i>"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="📤 Поделиться ссылкой",
                url=f"https://t.me/share/url?url={invite_link}&text=Бронируй%20ПК%20через%20Digital%20Arena!"
            )
        ]])

        await message.answer(text, parse_mode="HTML", reply_markup=keyboard)


async def process_referral_on_start(user: User, start_param: str, session) -> None:
    """
    Called when a user starts the bot with ?start=ref_CODE.
    Links the new user to the referrer.
    """
    if not start_param.startswith("ref_"):
        return
    ref_code = start_param[4:]

    # Don't self-refer
    if user.referral_code == ref_code:
        return
    # Only link once
    if user.referred_by:
        return

    referrer_result = await session.execute(
        select(User).where(User.referral_code == ref_code)
    )
    referrer = referrer_result.scalars().first()

    if referrer and referrer.id != user.id:
        user.referred_by = referrer.id
        await session.commit()
