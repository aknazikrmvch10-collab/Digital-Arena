"""
utils/booking_display.py

Shared helpers for rendering booking lists in Telegram messages.
Eliminates duplicate code in handlers/clubs.py.
"""
from datetime import timezone, timedelta
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

TASHKENT_TZ = timezone(timedelta(hours=5))

STATUS_MAP = {
    "CONFIRMED": ("🟡", "Ожидает"),
    "ACTIVE":    ("🟢", "Играет"),
    "COMPLETED": ("✅", "Завершено"),
    "NO_SHOW":   ("❌", "Не пришел"),
    "CANCELLED": ("❌", "Отменено"),
}


def render_bookings_text(bookings) -> str:
    """Build the text listing for a user's bookings."""
    if not bookings:
        return "📋 <b>Мои брони</b>\n\nУ вас пока нет бронирований."

    text = "📋 <b>Мои брони</b>\n\n"
    for b in bookings:
        club = b.club
        emoji, status_text = STATUS_MAP.get(b.status, ("⏳", b.status))
        start = b.start_time.astimezone(TASHKENT_TZ).strftime('%d.%m %H:%M')
        end   = b.end_time.astimezone(TASHKENT_TZ).strftime('%H:%M')
        text += f"{emoji} <b>{b.computer_name}</b> в {club.name}\n"
        text += f"  {start} - {end}\n"
        text += f"  Статус: {status_text}\n\n"
    return text


def build_bookings_keyboard(bookings) -> InlineKeyboardMarkup:
    """Build inline keyboard for booking list: show code / cancel / clear history / back."""
    buttons = []

    for b in bookings:
        if b.status in ["CONFIRMED", "ACTIVE"]:
            row = []
            if getattr(b, "confirmation_code", None):
                row.append(InlineKeyboardButton(
                    text="🎟 Показать код",
                    callback_data=f"show_code:{b.id}"
                ))
            if b.status == "CONFIRMED":
                row.append(InlineKeyboardButton(
                    text="❌ Отменить",
                    callback_data=f"cancel_booking:{b.id}"
                ))
            if row:
                buttons.append(row)

    has_old = any(b.status in ("COMPLETED", "CANCELLED", "NO_SHOW") for b in bookings)
    if has_old:
        buttons.append([InlineKeyboardButton(
            text="🗑 Очистить историю", callback_data="clear_history"
        )])

    buttons.append([InlineKeyboardButton(text="« Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
