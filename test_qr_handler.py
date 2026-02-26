import asyncio
from unittest.mock import AsyncMock, MagicMock
from aiogram.types import CallbackQuery, User, Message

# To load env vars
from dotenv import load_dotenv
load_dotenv()

from handlers.clubs import show_booking_code

async def run_test():
    try:
        user = User(id=1687679805, is_bot=False, first_name='Test')
        msg = MagicMock(spec=Message)
        msg.answer_photo = AsyncMock()
        
        callback = MagicMock(spec=CallbackQuery)
        callback.id = '1'
        callback.from_user = user
        # We need a valid booking ID from the DB that belongs to this user.
        # But we don't know one. Let's just pass any ID. It will either say "Бронь не найдена"
        # or it will fail on some other line.
        callback.data = 'show_code:1'
        callback.answer = AsyncMock()
        callback.message = msg
        
        print("Calling show_booking_code...")
        await show_booking_code(callback)
        print("Success! answer calls:", callback.answer.call_args_list)
        print("answer_photo calls:", msg.answer_photo.call_args_list)

    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_test())
