"""
Promo code handler.
/promo — enter a promo code to get a discount on the next booking.
Admin can create codes via /admin → Промокоды.
"""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select
from database import async_session_factory
from models import PromoCode, User
from utils.logging import get_logger

logger = get_logger(__name__)
router = Router()


class PromoStates(StatesGroup):
    waiting_for_code = State()
    # Admin create promo
    admin_create_code = State()
    admin_create_discount = State()
    admin_create_max_uses = State()


@router.message(Command("promo"))
async def cmd_promo(message: Message, state: FSMContext):
    """Ask user for promo code."""
    await message.answer(
        "🎫 <b>Промокод</b>\n\n"
        "Введите ваш промокод, чтобы получить скидку на следующую бронь:\n"
        "<i>Например: ARENA20</i>",
        parse_mode="HTML"
    )
    await state.set_state(PromoStates.waiting_for_code)


@router.message(PromoStates.waiting_for_code)
async def process_promo_code(message: Message, state: FSMContext):
    """Validate and save promo code to session."""
    code = message.text.strip().upper()
    await state.clear()

    async with async_session_factory() as session:
        result = await session.execute(
            select(PromoCode).where(PromoCode.code == code)
        )
        promo = result.scalars().first()

        if not promo or not promo.is_valid():
            await message.answer(
                "❌ <b>Промокод недействителен</b>\n\n"
                "Проверьте правильность кода или попробуйте другой.",
                parse_mode="HTML"
            )
            return

        # Save to user's session (FSM data with booking)
        # We store in a persistent key via FSM so the booking flow can use it
        await state.update_data(active_promo_code=code, active_promo_discount=promo.discount_percent)

        await message.answer(
            f"✅ <b>Промокод принят!</b>\n\n"
            f"Код: <code>{code}</code>\n"
            f"Скидка: <b>{promo.discount_percent}%</b>\n\n"
            f"Скидка будет применена при следующем бронировании.\n"
            f"Откройте мини-апп или выберите клуб для бронирования!",
            parse_mode="HTML"
        )


# ---- Admin: Create promo code ----

@router.callback_query(F.data == "admin_promo_create")
async def admin_create_promo_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "🎫 <b>Создание промокода</b>\n\n"
        "Введите код (например: <code>ARENA20</code>):",
        parse_mode="HTML"
    )
    await state.set_state(PromoStates.admin_create_code)


@router.message(PromoStates.admin_create_code)
async def admin_promo_get_code(message: Message, state: FSMContext):
    code = message.text.strip().upper()
    # Check uniqueness
    async with async_session_factory() as session:
        existing = await session.execute(select(PromoCode).where(PromoCode.code == code))
        if existing.scalars().first():
            await message.answer("❌ Этот код уже существует. Введите другой:")
            return
    await state.update_data(promo_code=code)
    await message.answer(f"➡️ Код: <code>{code}</code>\n\nВведите размер скидки в % (например: <code>15</code>):", parse_mode="HTML")
    await state.set_state(PromoStates.admin_create_discount)


@router.message(PromoStates.admin_create_discount)
async def admin_promo_get_discount(message: Message, state: FSMContext):
    try:
        discount = int(message.text.strip())
        if not (1 <= discount <= 100):
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите число от 1 до 100:")
        return
    await state.update_data(promo_discount=discount)
    await message.answer(
        f"Скидка: {discount}%\n\n"
        "Сколько раз можно использовать? (введите число или <code>0</code> для безлимита):",
        parse_mode="HTML"
    )
    await state.set_state(PromoStates.admin_create_max_uses)


@router.message(PromoStates.admin_create_max_uses)
async def admin_promo_create_finish(message: Message, state: FSMContext):
    try:
        max_uses = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите целое число:")
        return

    data = await state.get_data()
    await state.clear()

    async with async_session_factory() as session:
        async with session.begin():
            promo = PromoCode(
                code=data['promo_code'],
                discount_percent=data['promo_discount'],
                max_uses=max_uses if max_uses > 0 else None,
                created_by_tg_id=message.from_user.id
            )
            session.add(promo)

    await message.answer(
        f"✅ <b>Промокод создан!</b>\n\n"
        f"🎫 Код: <code>{data['promo_code']}</code>\n"
        f"💸 Скидка: {data['promo_discount']}%\n"
        f"🔢 Макс. использований: {'Безлимит' if max_uses == 0 else max_uses}",
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin_promo_list")
async def admin_promo_list(callback: CallbackQuery):
    """Show all active promo codes with delete options."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(PromoCode).where(PromoCode.is_active == True).order_by(PromoCode.created_at.desc()).limit(20)
        )
        promos = result.scalars().all()

    kb_buttons = []
    
    if not promos:
        text = "📭 <b>Нет активных промокодов</b>"
    else:
        text = "🎫 <b>Активные промокоды:</b>\nНажмите на промокод, чтобы удалить его (деактивировать)."
        for p in promos:
            uses = f"{p.uses_count}/{p.max_uses}" if p.max_uses else f"{p.uses_count}/∞"
            btn_text = f"❌ {p.code} — {p.discount_percent}% ({uses})"
            kb_buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"admin_promo_delete:{p.id}")])

    kb_buttons.append([InlineKeyboardButton(text="➕ Создать промокод", callback_data="admin_promo_create")])
    kb_buttons.append([InlineKeyboardButton(text="« Назад", callback_data="admin_back_main")])
    
    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data.startswith("admin_promo_delete:"))
async def admin_promo_delete(callback: CallbackQuery):
    """Deactivate (delete) a promo code."""
    promo_id = int(callback.data.split(":")[1])
    
    async with async_session_factory() as session:
        async with session.begin():
            promo = await session.get(PromoCode, promo_id)
            if promo:
                promo.is_active = False
                
    await callback.answer(f"Промокод удалён!", show_alert=True)
    # Refresh the list
    await admin_promo_list(callback)
