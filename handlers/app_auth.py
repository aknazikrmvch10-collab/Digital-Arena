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
from utils.timezone import now_tashkent, now_utc
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
        from keyboards.main import get_main_reply_keyboard
        await message.answer(
            "⚠️ Пожалуйста, поделитесь <b>своим</b> номером телефона.",
            reply_markup=get_main_reply_keyboard(),
            parse_mode="HTML"
        )
        return

    try:
        phone = contact.phone_number
        if not phone.startswith("+"):
            phone = "+" + phone

        tg_id = message.from_user.id
        code = _generate_code()
        # IMPORTANT: Use naive UTC for DB storage (matches timezone.py convention)
        now = now_utc()
        expires = now + timedelta(minutes=10)

        async with async_session_factory() as session:
            # 1. Save phone number to base User model
            from sqlalchemy import select
            user_result = await session.execute(
                select(User).where(User.tg_id == tg_id)
            )
            user = user_result.scalars().first()
            if user:
                user.phone = phone

            # 2. Invalidate any existing unused codes for this user
            from sqlalchemy import update
            await session.execute(
                update(AppAuthCode)
                .where(AppAuthCode.user_id == tg_id, AppAuthCode.used == False)
                .values(used=True)
            )

            # 3. Create new code
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
            f"• Введите ваш номер телефона\n"
            f"• Этот код: <code>{code}</code>",
            reply_markup=get_main_reply_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        import traceback
        err_str = traceback.format_exc()
        await message.answer(f"❌ Internal Server Error:\n<pre>{err_str[-1000:]}</pre>", parse_mode="HTML")


# ========== /setpassword — create password for multi-device login ==========
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

class PasswordStates(StatesGroup):
    waiting_for_password = State()
    waiting_for_confirm = State()

@router.message(Command("setpassword"))
async def cmd_setpassword(message: Message, state: FSMContext):
    """Allow user to create a password for logging in from any device."""
    await state.set_state(PasswordStates.waiting_for_password)
    await message.answer(
        "🔐 <b>Создание пароля для входа в приложение</b>\n\n"
        "Введите <b>новый пароль</b> (минимум 6 символов).\n"
        "После этого вы сможете входить в Digital Arena\n"
        "с любого устройства через номер телефона + пароль.\n\n"
        "✏️ <i>Введите пароль:</i>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove()
    )

@router.message(PasswordStates.waiting_for_password)
async def got_password(message: Message, state: FSMContext):
    pw = message.text.strip()
    if len(pw) < 6:
        await message.answer("⚠️ Пароль должен быть минимум 6 символов. Попробуйте снова:")
        return
    await state.update_data(password=pw)
    await state.set_state(PasswordStates.waiting_for_confirm)
    await message.answer("🔁 Повторите пароль для подтверждения:")

@router.message(PasswordStates.waiting_for_confirm)
async def got_password_confirm(message: Message, state: FSMContext):
    data = await state.get_data()
    pw = data.get("password", "")
    pw2 = message.text.strip()

    if pw != pw2:
        await state.set_state(PasswordStates.waiting_for_password)
        await message.answer("❌ Пароли не совпадают. Начните заново — введите новый пароль:")
        return

    # Hash and save
    import hashlib, uuid as _uuid
    from sqlalchemy import select as _select
    salt = str(_uuid.uuid4())[:8]
    pw_hash = hashlib.sha256(f"{pw}{salt}".encode()).hexdigest()
    password_hash = f"{salt}${pw_hash}"

    tg_id = message.from_user.id
    async with async_session_factory() as session:
        result = await session.execute(_select(User).where(User.tg_id == tg_id))
        user = result.scalars().first()
        if not user:
            await message.answer("❌ Аккаунт не найден. Сначала зарегистрируйтесь через /start")
            await state.clear()
            return
        phone = user.phone or "—"
        user.password_hash = password_hash
        await session.commit()

    await state.clear()
    await message.answer(
        f"✅ <b>Пароль успешно создан!</b>\n\n"
        f"Теперь вы можете войти в приложение с любого устройства:\n"
        f"• 📱 <b>Телефон:</b> <code>{phone}</code>\n"
        f"• 🔐 <b>Пароль:</b> ваш только что созданный пароль\n\n"
        f"Откройте приложение → вкладка «🔐 Пароль» → введите данные.",
        parse_mode="HTML",
        reply_markup=get_main_reply_keyboard()
    )

