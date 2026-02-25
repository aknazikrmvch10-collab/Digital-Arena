from aiogram import Router, F
from aiogram.types import Message
import json

router = Router()

@router.message(F.web_app_data)
async def handle_web_app_data(message: Message):
    """Handle data from Web App - computer selection"""
    try:
        data = json.loads(message.web_app_data.data)
        club_id = data.get('club_id')
        computer_id = data.get('computer_id')
        computer_name = data.get('computer_name')
        price = data.get('price')
        
        # Show confirmation with booking flow
        from keyboards.main import get_date_keyboard
        
        await message.answer(
            f"✅ <b>Компьютер выбран!</b>\n\n"
            f"💻 {computer_name}\n"
            f"💰 {price} сум/час\n\n"
            f"📅 Выберите дату бронирования:",
            reply_markup=get_date_keyboard(club_id, computer_id),
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(
            f"❌ Ошибка обработки данных: {str(e)}\n\n"
            "Попробуйте выбрать компьютер снова."
        )
