from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_admin_main_menu() -> InlineKeyboardMarkup:
    """Main menu for admin panel."""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="📊 Статистика", callback_data="admin_stats")
    builder.button(text="🏢 Управление клубами", callback_data="admin_clubs")
    builder.button(text="📢 Рассылка", callback_data="admin_broadcast")
    builder.button(text="🎫 Промокоды", callback_data="admin_promo_list")
    builder.button(text="❌ Закрыть", callback_data="admin_close")
    
    builder.adjust(1)
    return builder.as_markup()

def get_admin_clubs_menu(clubs: list) -> InlineKeyboardMarkup:
    """Menu to manage clubs."""
    builder = InlineKeyboardBuilder()
    
    # Add existing clubs
    for club in clubs:
        builder.button(text=f"🏢 {club.name}", callback_data=f"admin_club:{club.id}")
        
    builder.button(text="➕ Добавить клуб", callback_data="admin_add_club")
    builder.button(text="« Назад", callback_data="admin_back_main")
    
    builder.adjust(1)
    return builder.as_markup()

def get_driver_type_keyboard() -> InlineKeyboardMarkup:
    """Keyboard to select driver type."""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="🖥 MOCK (Тестовый)", callback_data="driver:MOCK")
    builder.button(text="☁️ ICAFE Cloud", callback_data="driver:ICAFE")
    builder.button(text="🌐 SmartShell", callback_data="driver:SMARTSHELL")
    builder.button(text="⚡️ Langame", callback_data="driver:LANGAME")
    builder.button(text="🔌 Standalone (Ручной)", callback_data="driver:STANDALONE")
    
    builder.adjust(1)
    return builder.as_markup()

def get_venue_type_keyboard() -> InlineKeyboardMarkup:
    """Keyboard to select venue type."""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="🎮 Компьютерный клуб", callback_data="venue_type:computer_club")
    builder.button(text="🍽 Ресторан", callback_data="venue_type:restaurant")
    
    builder.adjust(1)
    return builder.as_markup()

def get_club_detail_menu(club_id: int, venue_type: str = "computer_club") -> InlineKeyboardMarkup:
    """Menu for club details with item management."""
    builder = InlineKeyboardBuilder()
    
    items_label = "💻 Компьютеры" if venue_type == "computer_club" else "🍽 Столы"
    
    builder.button(text=items_label, callback_data=f"admin_club_computers:{club_id}") # Kept callback same for simplicity or update? Let's keep for now.
    builder.button(text="⚙️ Настройки", callback_data=f"admin_club_settings:{club_id}")
    builder.button(text="🗑 Удалить", callback_data=f"admin_delete_club:{club_id}")
    builder.button(text="« Назад", callback_data="admin_clubs")
    
    builder.adjust(1)
    return builder.as_markup()

def get_club_settings_menu(club_id: int) -> InlineKeyboardMarkup:
    """Menu for club settings."""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="📝 Изменить описание", callback_data=f"edit_club_desc:{club_id}")
    builder.button(text="🕒 Изменить часы работы", callback_data=f"edit_club_hours:{club_id}")
    builder.button(text="📸 Изменить фото", callback_data=f"edit_club_photo:{club_id}")
    builder.button(text="📶 Изменить Wi-Fi", callback_data=f"edit_club_wifi:{club_id}")
    builder.button(text="« Назад", callback_data=f"admin_club:{club_id}")
    
    builder.adjust(1)
    return builder.as_markup()

def get_computers_list_menu(club_id: int, items: list, venue_type: str = "computer_club") -> InlineKeyboardMarkup:
    """Menu showing list of items (computers or tables)."""
    builder = InlineKeyboardBuilder()
    
    # Group by zone
    zones = {}
    for item in items:
        zone = item.zone or "Без зоны"
        if zone not in zones:
            zones[zone] = []
        zones[zone].append(item)
    
    for zone, group_items in zones.items():
        for item in group_items:
            # Handle different price attributes or unify them? 
            # Computer: price_per_hour
            # Table: boooking_price or min_deposit
            price = "0"
            if hasattr(item, 'price_per_hour'):
                price = f"{item.price_per_hour} сум/ч"
            elif hasattr(item, 'min_deposit'):
                price = f"Деп: {item.min_deposit}"
                
            builder.button(
                text=f"{item.name} ({zone}) - {price}",
                # callback_data needs to handle item type or ID collision? 
                # IDs are unique per table, but tables are different.
                # Let's say item.id is enough if we know the context.
                callback_data=f"admin_item_view:{item.id}:{venue_type}" 
            )
    
    add_label = "➕ Добавить ПК" if venue_type == "computer_club" else "➕ Добавить стол"
    builder.button(text=add_label, callback_data=f"admin_add_computer:{club_id}") # Reuse callback, handle in handler
    builder.button(text="« Назад", callback_data=f"admin_club:{club_id}")
    
    builder.adjust(1)
    return builder.as_markup()

def get_zone_selection_keyboard(venue_type: str = "computer_club") -> InlineKeyboardMarkup:
    """Keyboard to select zone."""
    builder = InlineKeyboardBuilder()
    
    if venue_type == "restaurant":
        builder.button(text="🌅 Терраса", callback_data="zone:Terrace")
        builder.button(text="🏠 Основной зал", callback_data="zone:Main Hall")
        builder.button(text="💎 VIP", callback_data="zone:VIP")
    else:
        builder.button(text="🟢 Standard", callback_data="zone:Standard")
        builder.button(text="🟡 VIP", callback_data="zone:VIP")
        builder.button(text="🔴 Pro", callback_data="zone:Pro")
    
    builder.adjust(1)
    return builder.as_markup()
