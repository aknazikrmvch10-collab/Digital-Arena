"""
Internationalization (i18n) module for Digital Arena.
Provides translated strings for RU, UZ, KZ languages.
"""
from typing import Dict

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    'ru': {
        'start_welcome': (
            "👋 <b>Добро пожаловать в Digital Arena!</b>\n\n"
            "🎮 Бронируй компьютеры и столики без очередей.\n\n"
            "Выбери язык / Tilni tanlang / Тілді таңдаңыз:"
        ),
        'choose_language': "🌍 Выберите язык:",
        'language_set': "✅ Язык изменён на Русский 🇷🇺",
        'select_club': "🏢 Выберите клуб:",
        'book_now': "📅 Забронировать",
        'my_bookings': "📋 Мои брони",
        'settings': "⚙️ Настройки",
        'referral': "🎁 Реферальная программа",
        'no_bookings': "📋 У вас пока нет броней.",
        'booking_confirmed': "✅ <b>Бронь подтверждена!</b>",
        'booking_cancelled': "❌ Бронь отменена.",
        'enter_promo': "🎫 Введите промокод:",
        'promo_applied': "✅ Промокод <b>{code}</b> применён! Скидка {discount}%",
        'promo_invalid': "❌ Промокод недействителен или истёк.",
        'promo_already_used': "❌ Вы уже использовали этот промокод.",
        'help_text': (
            "🆘 <b>Помощь</b>\n\n"
            "/start — главное меню\n"
            "/profile — мой профиль\n"
            "/referral — реферальная программа\n"
            "/promo — ввести промокод\n"
            "/settings — настройки"
        ),
    },
    'uz': {
        'start_welcome': (
            "👋 <b>Digital Arena'ga xush kelibsiz!</b>\n\n"
            "🎮 Kompyuter va stol bronlash navbatsiz.\n\n"
            "Tilni tanlang:"
        ),
        'choose_language': "🌍 Tilni tanlang:",
        'language_set': "✅ Til o'zbekchaga o'zgartirildi 🇺🇿",
        'select_club': "🏢 Klub tanlang:",
        'book_now': "📅 Bronlash",
        'my_bookings': "📋 Bronlarim",
        'settings': "⚙️ Sozlamalar",
        'referral': "🎁 Referal dastur",
        'no_bookings': "📋 Hali bronlaringiz yo'q.",
        'booking_confirmed': "✅ <b>Bron tasdiqlandi!</b>",
        'booking_cancelled': "❌ Bron bekor qilindi.",
        'enter_promo': "🎫 Promokodni kiriting:",
        'promo_applied': "✅ Promokod <b>{code}</b> qo'llandi! {discount}% chegirma",
        'promo_invalid': "❌ Promokod yaroqsiz yoki muddati o'tgan.",
        'promo_already_used': "❌ Siz bu promokodni allaqachon ishlatgansiz.",
        'help_text': (
            "🆘 <b>Yordam</b>\n\n"
            "/start — asosiy menyu\n"
            "/profile — mening profilim\n"
            "/referral — referal dastur\n"
            "/promo — promokod kiritish\n"
            "/settings — sozlamalar"
        ),
    },
    'kz': {
        'start_welcome': (
            "👋 <b>Digital Arena-ға қош келдіңіз!</b>\n\n"
            "🎮 Компьютер мен үстелді кезексіз брондаңыз.\n\n"
            "Тілді таңдаңыз:"
        ),
        'choose_language': "🌍 Тілді таңдаңыз:",
        'language_set': "✅ Тіл қазақшаға өзгертілді 🇰🇿",
        'select_club': "🏢 Клубты таңдаңыз:",
        'book_now': "📅 Брондау",
        'my_bookings': "📋 Брондарым",
        'settings': "⚙️ Параметрлер",
        'referral': "🎁 Реферал бағдарлама",
        'no_bookings': "📋 Сізде әлі брондар жоқ.",
        'booking_confirmed': "✅ <b>Брон расталды!</b>",
        'booking_cancelled': "❌ Брон бас тартылды.",
        'enter_promo': "🎫 Промокодты енгізіңіз:",
        'promo_applied': "✅ Промокод <b>{code}</b> қолданылды! {discount}% жеңілдік",
        'promo_invalid': "❌ Промокод жарамсыз немесе мерзімі өткен.",
        'promo_already_used': "❌ Сіз бұл промокодты бұрын пайдалантыңыз.",
        'help_text': (
            "🆘 <b>Анықтама</b>\n\n"
            "/start — басты мәзір\n"
            "/profile — менің профилім\n"
            "/referral — реферал бағдарлама\n"
            "/promo — промокод енгізу\n"
            "/settings — параметрлер"
        ),
    }
}


def t(user_language: str, key: str, **kwargs) -> str:
    """Get translated string for the given language and key."""
    lang = user_language if user_language in TRANSLATIONS else 'ru'
    text = TRANSLATIONS[lang].get(key) or TRANSLATIONS['ru'].get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text


async def get_user_lang(user_tg_id: int) -> str:
    """Fetch user's language preference from DB."""
    from database import async_session_factory
    from models import User
    from sqlalchemy import select
    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.tg_id == user_tg_id))
        user = result.scalars().first()
        if user and getattr(user, 'language', None):
            return user.language
    return 'ru'
