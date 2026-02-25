from aiogram.types import Message, InlineKeyboardMarkup
from typing import Optional
from contextlib import suppress
from aiogram.exceptions import TelegramBadRequest

async def safe_edit(message: Message, text: str, reply_markup: Optional[InlineKeyboardMarkup] = None, parse_mode: str = "HTML") -> None:
    """Edit a message safely. Catches all TelegramBadRequest errors."""
    with suppress(TelegramBadRequest):
        await message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)

async def safe_delete(message: Message) -> None:
    """Safely delete a message, ignoring errors if it can't be deleted."""
    with suppress(TelegramBadRequest):
        await message.delete()
