"""
Admin Broadcast handler.
Allows super-admins to send a message to all users in the database.
/admin → Рассылка
"""
from aiogram import Router, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select, func
from database import async_session_factory
from models import User
from utils.logging import get_logger

logger = get_logger(__name__)
router = Router()


class BroadcastStates(StatesGroup):
    waiting_for_message = State()
    waiting_for_confirm = State()


@router.callback_query(F.data == "admin_broadcast")
async def start_broadcast(callback: CallbackQuery, state: FSMContext):
    """Start broadcast flow."""
    await callback.message.edit_text(
        "📢 <b>Рассылка всем пользователям</b>\n\n"
        "Введите текст сообщения. Поддерживается HTML-разметка.\n\n"
        "<i>Пример: &lt;b&gt;Акция!&lt;/b&gt; Сегодня скидка 20% на все брони!</i>",
        parse_mode="HTML"
    )
    await state.set_state(BroadcastStates.waiting_for_message)


@router.message(BroadcastStates.waiting_for_message)
async def broadcast_preview(message: Message, state: FSMContext):
    """Show preview of the broadcast message."""
    text = message.text or message.caption or ""
    await state.update_data(broadcast_text=text)

    async with async_session_factory() as session:
        total = await session.scalar(select(func.count(User.id))) or 0

    preview_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"✅ Отправить всем ({total} чел.)", callback_data="broadcast_confirm"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="broadcast_cancel"),
        ]
    ])

    await message.answer(
        f"📋 <b>Предпросмотр:</b>\n\n{text}\n\n"
        f"👥 Получателей: <b>{total}</b>",
        parse_mode="HTML",
        reply_markup=preview_kb
    )
    await state.set_state(BroadcastStates.waiting_for_confirm)


@router.callback_query(F.data == "broadcast_cancel")
async def broadcast_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Рассылка отменена.")


@router.callback_query(F.data == "broadcast_confirm")
async def broadcast_send(callback: CallbackQuery, state: FSMContext):
    """Send the broadcast to all users."""
    data = await state.get_data()
    text = data.get("broadcast_text", "")
    await state.clear()

    await callback.message.edit_text("⏳ Отправляю рассылку...")

    async with async_session_factory() as session:
        result = await session.execute(select(User.tg_id))
        tg_ids = [row[0] for row in result.all()]

    sent = 0
    failed = 0
    for tg_id in tg_ids:
        try:
            await callback.bot.send_message(
                chat_id=tg_id,
                text=text,
                parse_mode="HTML"
            )
            sent += 1
        except Exception:
            failed += 1

    logger.info("Broadcast complete", sent=sent, failed=failed)
    await callback.message.edit_text(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"📨 Отправлено: {sent}\n"
        f"❌ Не доставлено: {failed}",
        parse_mode="HTML"
    )
