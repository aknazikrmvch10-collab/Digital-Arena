from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List
from models import Club

def get_main_menu() -> InlineKeyboardMarkup:
    """Main menu keyboard."""
    buttons = [
        [InlineKeyboardButton(text="🔍 Найти клубы", callback_data="find_clubs")],
        [InlineKeyboardButton(text="📋 Мои брони", callback_data="my_bookings")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")],
        [InlineKeyboardButton(text="ℹ️ О боте", callback_data="about")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_main_reply_keyboard():
    """Persistent main menu keyboard."""
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
    
    buttons = [
        [KeyboardButton(text="🏢 Клубы"), KeyboardButton(text="👤 Мои брони")],
        [KeyboardButton(text="⚙️ Настройки"), KeyboardButton(text="🆘 Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_clubs_keyboard(clubs: List[Club]) -> InlineKeyboardMarkup:
    """List of clubs as inline buttons."""
    buttons = []
    for club in clubs:
        buttons.append([
            InlineKeyboardButton(
                text=f"{club.name} ({club.city})",
                callback_data=f"club:{club.id}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="« Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_club_detail_keyboard(club_id: int) -> InlineKeyboardMarkup:
    """Club detail actions."""
    from config import settings as settings_config
    buttons = []
    
    # Only show Mini App button if BASE_URL is configured
    if settings_config.BASE_URL:
        from aiogram.types import WebAppInfo
        buttons.append([InlineKeyboardButton(
            text="🕹️ Выбрать место (Mini App)", 
            web_app=WebAppInfo(url=f"{settings_config.BASE_URL}/miniapp/index.html?club_id={club_id}&v=14")
        )])
    
    buttons.extend([
        [InlineKeyboardButton(text="💻 Посмотреть компьютеры", callback_data=f"view_pcs:{club_id}")],
        [InlineKeyboardButton(text="📍 Местоположение", callback_data=f"location:{club_id}")],
        [InlineKeyboardButton(text="« Назад к списку", callback_data="find_clubs")]
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_computers_keyboard(club_id: int, computers: list, page: int = 0) -> InlineKeyboardMarkup:
    """Show available computers with specs if available. Paginated (max 20 per page)."""
    PAGE_SIZE = 20
    total = len(computers)
    start = page * PAGE_SIZE
    end = min(start + PAGE_SIZE, total)
    page_computers = computers[start:end]
    
    buttons = []
    for pc in page_computers:
        status = "✅" if getattr(pc, 'is_available', True) else "❌"
        
        # Build compact spec display
        if pc.gpu and pc.ram_gb and pc.monitor_hz:
            spec_text = f"{pc.gpu} {pc.ram_gb}GB {pc.monitor_hz}Hz"
            price_k = int(pc.price_per_hour / 1000)
            text = f"{status} {pc.name} | {spec_text} | {price_k}k сум"
        else:
            text = f"{status} {pc.name} - {pc.zone} ({int(pc.price_per_hour)} сум/час)"
        
        buttons.append([
            InlineKeyboardButton(
                text=text,
                callback_data=f"book:{club_id}:{pc.id}"
            )
        ])
    
    # Pagination buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"pc_page:{club_id}:{page-1}"))
    if end < total:
        nav_buttons.append(InlineKeyboardButton(text=f"➡️ Ещё ({total - end})", callback_data=f"pc_page:{club_id}:{page+1}"))
    if nav_buttons:
        buttons.append(nav_buttons)
    
    # Back to zones list
    buttons.append([InlineKeyboardButton(text="« Назад к зонам", callback_data=f"view_pcs:{club_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_date_keyboard(club_id: int, pc_id: str) -> InlineKeyboardMarkup:
    """Select booking date."""
    from datetime import datetime, timedelta
    from utils.timezone import now_tashkent
    today = now_tashkent()
    tomorrow = today + timedelta(days=1)
    
    buttons = [
        [InlineKeyboardButton(text=f"📅 Сегодня ({today.strftime('%d.%m')})", callback_data=f"date:{club_id}:{pc_id}:0")],
        [InlineKeyboardButton(text=f"📅 Завтра ({tomorrow.strftime('%d.%m')})", callback_data=f"date:{club_id}:{pc_id}:1")],
        [InlineKeyboardButton(text="« Назад к компьютерам", callback_data=f"view_pcs:{club_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

async def get_time_keyboard(club_id: int, pc_id: str, day_offset: int) -> InlineKeyboardMarkup:
    """Select booking time (10:00-22:00) with availability indicators."""
    from database import async_session_factory
    from models import Booking
    from sqlalchemy import select, and_
    from datetime import datetime, timedelta
    from utils.timezone import now_tashkent
    
    # Calculate the selected date
    selected_date = (now_tashkent() + timedelta(days=day_offset)).date()
    
    buttons = []
    
    async with async_session_factory() as session:
        # Query bookings for this PC on the selected date using item_id (reliable)
        result = await session.execute(
            select(Booking).where(
                and_(
                    Booking.item_id == int(pc_id),
                    Booking.club_id == int(club_id),
                    Booking.status.in_(["CONFIRMED", "ACTIVE"])
                )
            )
        )
        bookings = result.scalars().all()
        
        # Filter bookings for the selected date
        occupied_hours = set()
        for booking in bookings:
            if booking.start_time.date() == selected_date:
                # Mark ALL hours that this booking covers as occupied
                from datetime import timedelta
                current = booking.start_time
                while current < booking.end_time:
                    occupied_hours.add(current.hour)
                    current += timedelta(hours=1)
    
    # Show all 24 hours (24/7 operation)
    for hour in range(24):
        if hour in occupied_hours:
            button_text = f"❌ {hour:02d}:00"
        else:
            button_text = f"✅ {hour:02d}:00"
        
        buttons.append([
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"time:{club_id}:{pc_id}:{day_offset}:{hour}"
            )
        ])
    
    buttons.append([InlineKeyboardButton(text="« Назад к датам", callback_data=f"book:{club_id}:{pc_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_minute_keyboard(club_id: int, pc_id: str, day_offset: int, hour: int) -> InlineKeyboardMarkup:
    """Select start minute."""
    buttons = [
        [InlineKeyboardButton(text="🕐 :00", callback_data=f"minute:{club_id}:{pc_id}:{day_offset}:{hour}:0")],
        [InlineKeyboardButton(text="🕐 :15", callback_data=f"minute:{club_id}:{pc_id}:{day_offset}:{hour}:15")],
        [InlineKeyboardButton(text="🕐 :30", callback_data=f"minute:{club_id}:{pc_id}:{day_offset}:{hour}:30")],
        [InlineKeyboardButton(text="🕐 :45", callback_data=f"minute:{club_id}:{pc_id}:{day_offset}:{hour}:45")],
        [InlineKeyboardButton(text="« Назад", callback_data=f"date:{club_id}:{pc_id}:{day_offset}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_duration_keyboard(club_id: int, pc_id: str, day_offset: int, hour: int, minute: int) -> InlineKeyboardMarkup:
    """Select booking duration - simple fixed options."""
    buttons = [
        [InlineKeyboardButton(text="⏱ 30 минут", callback_data=f"duration:{club_id}:{pc_id}:{day_offset}:{hour}:{minute}:30")],
        [InlineKeyboardButton(text="⏱ 1 час", callback_data=f"duration:{club_id}:{pc_id}:{day_offset}:{hour}:{minute}:60")],
        [InlineKeyboardButton(text="⏱ 1 час 30 минут", callback_data=f"duration:{club_id}:{pc_id}:{day_offset}:{hour}:{minute}:90")],
        [InlineKeyboardButton(text="⏱ 2 часа", callback_data=f"duration:{club_id}:{pc_id}:{day_offset}:{hour}:{minute}:120")],
        [InlineKeyboardButton(text="⏱ 2 часа 30 минут", callback_data=f"duration:{club_id}:{pc_id}:{day_offset}:{hour}:{minute}:150")],
        [InlineKeyboardButton(text="⏱ 3 часа", callback_data=f"duration:{club_id}:{pc_id}:{day_offset}:{hour}:{minute}:180")],
        [InlineKeyboardButton(text="« Назад", callback_data=f"date:{club_id}:{pc_id}:{day_offset}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
