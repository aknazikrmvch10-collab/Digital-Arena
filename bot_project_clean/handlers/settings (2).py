from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select
from models import User
from database import async_session_factory

router = Router()

@router.callback_query(F.data == "settings")
@router.message(F.text == "⚙️ Настройки")
async def show_settings(event: Message | CallbackQuery):
    """Show user settings."""
    if isinstance(event, Message):
        message = event
        user_id = event.from_user.id
    else:
        message = event.message
        user_id = event.from_user.id
        
    async with async_session_factory() as session:
        result = await session.execute(
            select(User).where(User.tg_id == user_id)
        )
        user = result.scalars().first()
        
        if not user:
            if isinstance(event, CallbackQuery):
                await event.answer("\u0412\u044b \u043d\u0435 \u0437\u0430\u0440\u0435\u0433\u0438\u0441\u0442\u0440\u0438\u0440\u043e\u0432\u0430\u043d\u044b.", show_alert=True)
            else:
                await message.answer("\u0412\u044b \u043d\u0435 \u0437\u0430\u0440\u0435\u0433\u0438\u0441\u0442\u0440\u0438\u0440\u043e\u0432\u0430\u043d\u044b.")
            return
        
        notif_status = "✅ Включены" if user.notifications_enabled else "❌ Выключены"
        
        text = (
            f"⚙️ <b>Настройки уведомлений</b>\n\n"
            f"Статус: {notif_status}\n"
            f"Время напоминания: за {user.notification_minutes} минут\n\n"
            f"Настройте когда получать напоминания о бронях:"
        )
        
        toggle_text = "\U0001f515 \u0412\u044b\u043a\u043b\u044e\u0447\u0438\u0442\u044c" if user.notifications_enabled else "\U0001f514 \u0412\u043a\u043b\u044e\u0447\u0438\u0442\u044c"
        toggle_action = "notif_disable" if user.notifications_enabled else "notif_enable"
        
        buttons = [
            [InlineKeyboardButton(text=toggle_text, callback_data=toggle_action)],
            [InlineKeyboardButton(text="\U0001f4c5 \u0418\u0437\u043c\u0435\u043d\u0438\u0442\u044c \u0432\u0440\u0435\u043c\u044f", callback_data="notif_time")],
            [InlineKeyboardButton(text="\u00ab \u041d\u0430\u0437\u0430\u0434", callback_data="back_main")]
        ]
        
        await message.answer(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
            parse_mode="HTML"
        )

@router.callback_query(F.data == "notif_enable")
async def enable_notifications(callback: CallbackQuery):
    """Enable notifications."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(User).where(User.tg_id == callback.from_user.id)
        )
        user = result.scalars().first()
        
        if user:
            user.notifications_enabled = True
            await session.commit()
            await callback.answer("\u2705 \u0423\u0432\u0435\u0434\u043e\u043c\u043b\u0435\u043d\u0438\u044f \u0432\u043a\u043b\u044e\u0447\u0435\u043d\u044b!", show_alert=True)
            
            # Refresh settings page
            await show_settings(callback)

@router.callback_query(F.data == "notif_disable")
async def disable_notifications(callback: CallbackQuery):
    """Disable notifications."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(User).where(User.tg_id == callback.from_user.id)
        )
        user = result.scalars().first()
        
        if user:
            user.notifications_enabled = False
            await session.commit()
            await callback.answer("\U0001f515 \u0423\u0432\u0435\u0434\u043e\u043c\u043b\u0435\u043d\u0438\u044f \u0432\u044b\u043a\u043b\u044e\u0447\u0435\u043d\u044b", show_alert=True)
            
            # Refresh settings page
            await show_settings(callback)

@router.callback_query(F.data == "notif_time")
async def show_time_options(callback: CallbackQuery):
    """Show notification timing options."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(User).where(User.tg_id == callback.from_user.id)
        )
        user = result.scalars().first()
        
        if not user:
            await callback.answer("\u0412\u044b \u043d\u0435 \u0437\u0430\u0440\u0435\u0433\u0438\u0441\u0442\u0440\u0438\u0440\u043e\u0432\u0430\u043d\u044b.", show_alert=True)
            return

        text = (
            "\u23f0 <b>\u0412\u0440\u0435\u043c\u044f \u043d\u0430\u043f\u043e\u043c\u0438\u043d\u0430\u043d\u0438\u044f</b>\n\n"
            "\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435, \u0437\u0430 \u0441\u043a\u043e\u043b\u044c\u043a\u043e \u043c\u0438\u043d\u0443\u0442 \u0434\u043e \u0431\u0440\u043e\u043d\u0438 \u043f\u043e\u043b\u0443\u0447\u0430\u0442\u044c \u0443\u0432\u0435\u0434\u043e\u043c\u043b\u0435\u043d\u0438\u0435:"
        )
        
        buttons = [
            [InlineKeyboardButton(
                text=f"{'✅' if user.notification_minutes == 15 else '⏰'} \u0417\u0430 15 \u043c\u0438\u043d\u0443\u0442",
                callback_data="notif_set:15"
            )],
            [InlineKeyboardButton(
                text=f"{'✅' if user.notification_minutes == 30 else '⏰'} \u0417\u0430 30 \u043c\u0438\u043d\u0443\u0442",
                callback_data="notif_set:30"
            )],
            [InlineKeyboardButton(
                text=f"{'✅' if user.notification_minutes == 60 else '⏰'} \u0417\u0430 60 \u043c\u0438\u043d\u0443\u0442",
                callback_data="notif_set:60"
            )],
            [InlineKeyboardButton(text="\u00ab \u041d\u0430\u0437\u0430\u0434", callback_data="settings")]
        ]
        
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
            parse_mode="HTML"
        )

@router.callback_query(F.data.startswith("notif_set:"))
async def set_notification_time(callback: CallbackQuery):
    """Set notification timing."""
    minutes = int(callback.data.split(":")[1])
    
    async with async_session_factory() as session:
        result = await session.execute(
            select(User).where(User.tg_id == callback.from_user.id)
        )
        user = result.scalars().first()
        
        if user:
            user.notification_minutes = minutes
            await session.commit()
            await callback.answer(f"\u2705 \u0423\u0441\u0442\u0430\u043d\u043e\u0432\u043b\u0435\u043d\u043e: \u0437\u0430 {minutes} \u043c\u0438\u043d\u0443\u0442", show_alert=True)
            
            # Refresh time options page
            await show_time_options(callback)
