"""
utils/booking_display.py

Shared helpers for rendering booking lists in Telegram messages.
Eliminated duplicate code and added multi-language support.
"""
from datetime import timezone, timedelta
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from i18n import t

TASHKENT_TZ = timezone(timedelta(hours=5))

def get_status_display(status: str, lang: str = 'ru'):
    """Get status emoji and translated text."""
    status_map = {
        "CONFIRMED": ("🟡", t(lang, 'status_confirmed')),
        "ACTIVE":    ("🟢", t(lang, 'status_active')),
        "COMPLETED": ("✅", t(lang, 'status_completed')),
        "NO_SHOW":   ("❌", t(lang, 'status_noshow')),
        "CANCELLED": ("❌", t(lang, 'status_cancelled')),
    }
    return status_map.get(status, ("⏳", status))

def render_bookings_text(bookings, lang: str = 'ru') -> str:
    """Build the text listing for a user's bookings with translation."""
    if not bookings:
        return t(lang, 'no_bookings')

    text = f"📋 <b>{t(lang, 'my_bookings')}</b>\n\n"
    for b in bookings:
        club = b.club
        emoji, status_text = get_status_display(b.status, lang)
        start = b.start_time.astimezone(TASHKENT_TZ).strftime('%d.%m %H:%M')
        end   = b.end_time.astimezone(TASHKENT_TZ).strftime('%H:%M')
        
        # Localize item type (PC or Table)
        item_prefix = "🕹" # Default for PC
        if getattr(club, 'venue_type', 'computer_club') == 'restaurant':
            item_prefix = "🍽"
            
        text += f"{emoji} <b>{item_prefix} {b.computer_name}</b> in {club.name}\n"
        text += f"  {start} - {end}\n"
        text += f"  {t(lang, 'booking_status')}: {status_text}\n\n"
    return text

def build_bookings_keyboard(bookings, lang: str = 'ru') -> InlineKeyboardMarkup:
    """Build inline keyboard for booking list with translations."""
    buttons = []

    for b in bookings:
        if b.status in ["CONFIRMED", "ACTIVE"]:
            row = []
            if getattr(b, "confirmation_code", None):
                row.append(InlineKeyboardButton(
                    text=f"🎟 {t(lang, 'btn_show_code')}",
                    callback_data=f"show_code:{b.id}"
                ))
            if b.status == "CONFIRMED":
                row.append(InlineKeyboardButton(
                    text=f"❌ {t(lang, 'btn_cancel')}",
                    callback_data=f"cancel_booking:{b.id}"
                ))
            if row:
                buttons.append(row)

    has_old = any(b.status in ("COMPLETED", "CANCELLED", "NO_SHOW") for b in bookings)
    if has_old:
        buttons.append([InlineKeyboardButton(
            text=f"🗑 {t(lang, 'btn_clear_history')}", callback_data="clear_history"
        )])

    buttons.append([InlineKeyboardButton(text=t(lang, 'btn_back'), callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
