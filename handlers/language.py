"""
Language selection handler.
Lets users switch the bot interface between RU / UZ / KZ.
"""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select
from database import async_session_factory
from models import User
from i18n import t

router = Router()

LANGUAGE_KEYBOARD = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
        InlineKeyboardButton(text="🇺🇿 O'zbek", callback_data="lang:uz"),
        InlineKeyboardButton(text="🇰🇿 Қазақ", callback_data="lang:kz"),
    ]
])


@router.message(Command("language"))
async def cmd_language(message: Message):
    """Show language selection."""
    await message.answer("🌍 Выберите язык / Tanlang / Таңдаңыз:", reply_markup=LANGUAGE_KEYBOARD)


@router.callback_query(F.data.startswith("lang:"))
async def set_language(callback: CallbackQuery):
    """Save user language preference."""
    lang = callback.data.split(":")[1]
    if lang not in ('ru', 'uz', 'kz'):
        await callback.answer("Unknown language", show_alert=True)
        return

    async with async_session_factory() as session:
        async with session.begin():
            result = await session.execute(select(User).where(User.tg_id == callback.from_user.id))
            user = result.scalars().first()
            if user:
                user.language = lang
            else:
                user = User(tg_id=callback.from_user.id, language=lang,
                            full_name=callback.from_user.full_name)
                session.add(user)

    confirmation = {
        'ru': "✅ Язык изменён на Русский 🇷🇺",
        'uz': "✅ Til o'zbekchaga o'zgartirildi 🇺🇿",
        'kz': "✅ Тіл қазақшаға өзгертілді 🇰🇿",
    }
    await callback.message.edit_text(confirmation[lang])
    
    from keyboards.main import get_main_reply_keyboard
    await callback.message.answer(
        f"🎮 <b>Digital Arena</b>\n\n{t(lang, 'start_welcome')}",
        reply_markup=get_main_reply_keyboard(lang=lang),
        parse_mode="HTML"
    )
    await callback.answer()
