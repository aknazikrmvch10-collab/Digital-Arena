from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from typing import List
from models import Club
from i18n import t

def get_main_menu(lang: str = 'ru') -> InlineKeyboardMarkup:
    """Main inline menu keyboard."""
    buttons = [
        [InlineKeyboardButton(text=t(lang, 'btn_find_clubs'), callback_data="find_clubs")],
        [InlineKeyboardButton(text=t(lang, 'btn_my_bookings'), callback_data="my_bookings")],
        [InlineKeyboardButton(text=t(lang, 'btn_app'), callback_data="open_app")],
        [InlineKeyboardButton(text=t(lang, 'btn_about'), callback_data="about")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_main_reply_keyboard(lang: str = 'ru'):
    """Persistent main menu keyboard."""
    buttons = [
        [KeyboardButton(text=t(lang, 'btn_find_clubs')), KeyboardButton(text=t(lang, 'btn_my_bookings'))],
        [KeyboardButton(text=t(lang, 'btn_app')), KeyboardButton(text=t(lang, 'btn_help'))],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_clubs_keyboard(clubs: List[Club], lang: str = 'ru') -> InlineKeyboardMarkup:
    """List of clubs as inline buttons."""
    buttons = []
    for club in clubs:
        buttons.append([
            InlineKeyboardButton(
                text=f"{club.name} ({club.city})",
                callback_data=f"club:{club.id}"
            )
        ])
    buttons.append([InlineKeyboardButton(text=t(lang, 'btn_back'), callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_club_detail_keyboard(club_id: int, venue_type: str = 'computer_club', lang: str = 'ru') -> InlineKeyboardMarkup:
    """Club detail actions."""
    from config import settings as settings_config
    buttons = []
    is_restaurant = venue_type == 'restaurant'
    
    if settings_config.BASE_URL:
        mini_app_text = t(lang, 'select_table_miniapp' if is_restaurant else 'select_pc_miniapp')
        buttons.append([InlineKeyboardButton(
            text=mini_app_text, 
            web_app=WebAppInfo(url=f"{settings_config.BASE_URL}/miniapp/index.html?club_id={club_id}&v=14")
        )])
    
    if not is_restaurant:
        buttons.append([InlineKeyboardButton(text=t(lang, 'btn_view_pcs'), callback_data=f"view_pcs:{club_id}")])
    
    buttons.extend([
        [InlineKeyboardButton(text=t(lang, 'btn_location'), callback_data=f"location:{club_id}")],
        [InlineKeyboardButton(text=t(lang, 'btn_back_list'), callback_data="find_clubs")]
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_computers_keyboard(club_id: int, computers: list, lang: str = 'ru', page: int = 0) -> InlineKeyboardMarkup:
    """Show available computers with specs."""
    PAGE_SIZE = 20
    total = len(computers)
    start = page * PAGE_SIZE
    end = min(start + PAGE_SIZE, total)
    page_computers = computers[start:end]
    
    buttons = []
    for pc in page_computers:
        status = "✅" if getattr(pc, 'is_available', True) else "❌"
        if pc.gpu and pc.ram_gb and pc.monitor_hz:
            spec_text = f"{pc.gpu} {pc.ram_gb}GB {pc.monitor_hz}Hz"
            price_k = int(pc.price_per_hour / 1000)
            text = f"{status} {pc.name} | {spec_text} | {price_k}k сум"
        else:
            text = f"{status} {pc.name} - {pc.zone} ({int(pc.price_per_hour)} сум/час)"
        
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"book:{club_id}:{pc.id}")])
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text=t(lang, 'btn_back'), callback_data=f"pc_page:{club_id}:{page-1}"))
    if nav_buttons:
        buttons.append(nav_buttons)
    
    buttons.append([InlineKeyboardButton(text=t(lang, 'btn_back'), callback_data=f"view_pcs:{club_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ... other keyboards should also follow this pattern
