from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, ReplyKeyboardMarkup, KeyboardButton
from sqlalchemy import select

from models import User
from database import async_session_factory
from keyboards.main import get_main_menu
from utils.telegram_helpers import safe_delete

router = Router()

@router.callback_query(F.data == "confirm_age_18")
async def confirm_age(callback: CallbackQuery):
    """Handle age confirmation - then ask for phone number."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(User).where(User.tg_id == callback.from_user.id)
        )
        user = result.scalars().first()
        
        if user:
            user.age_confirmed = True
            await session.commit()
    
    await safe_delete(callback.message)
    
    # Check if we already have the phone
    if user and user.phone:
        from keyboards.main import get_main_reply_keyboard
        await callback.message.answer(
            "\u0421\u043f\u0430\u0441\u0438\u0431\u043e \u0437\u0430 \u043f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0435\u043d\u0438\u0435!\n\n"
            "\u0422\u0435\u043f\u0435\u0440\u044c \u0432\u044b \u043c\u043e\u0436\u0435\u0442\u0435 \u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u044c\u0441\u044f \u0432\u0441\u0435\u043c\u0438 \u0444\u0443\u043d\u043a\u0446\u0438\u044f\u043c\u0438 \u0431\u043e\u0442\u0430.",
            reply_markup=get_main_reply_keyboard(),
            parse_mode="HTML"
        )
    else:
        phone_keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="\U0001f4f1 \u041e\u0442\u043f\u0440\u0430\u0432\u0438\u0442\u044c \u043d\u043e\u043c\u0435\u0440", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await callback.message.answer(
            "\U0001f4f1 <b>\u041f\u043e\u0441\u043b\u0435\u0434\u043d\u0438\u0439 \u0448\u0430\u0433!</b>\n\n"
            "\u0414\u043b\u044f \u043f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0435\u043d\u0438\u044f \u0431\u0440\u043e\u043d\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u044f \u043d\u0430\u043c \u043d\u0443\u0436\u0435\u043d \u0432\u0430\u0448 \u043d\u043e\u043c\u0435\u0440 \u0442\u0435\u043b\u0435\u0444\u043e\u043d\u0430.\n"
            "\u0410\u0434\u043c\u0438\u043d\u0438\u0441\u0442\u0440\u0430\u0442\u043e\u0440 \u043a\u043b\u0443\u0431\u0430 \u0441\u043c\u043e\u0436\u0435\u0442 \u0441\u0432\u044f\u0437\u0430\u0442\u044c\u0441\u044f \u0441 \u0432\u0430\u043c\u0438, \u0435\u0441\u043b\u0438 \u0432\u043e\u0437\u043d\u0438\u043a\u043d\u0443\u0442 \u0432\u043e\u043f\u0440\u043e\u0441\u044b.\n\n"
            "\u041d\u0430\u0436\u043c\u0438\u0442\u0435 \u043a\u043d\u043e\u043f\u043a\u0443 \u043d\u0438\u0436\u0435 \U0001f447",
            reply_markup=phone_keyboard,
            parse_mode="HTML"
        )
    await callback.answer()


    await callback.answer()
