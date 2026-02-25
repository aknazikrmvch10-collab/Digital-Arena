from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_filters_main_keyboard(club_id: int) -> InlineKeyboardMarkup:
    """Main menu for selecting filter category."""
    buttons = [
        [InlineKeyboardButton(text="💎 По зоне", callback_data=f"filter_cat:{club_id}:zone")],
        [InlineKeyboardButton(text="🎮 По видеокарте", callback_data=f"filter_cat:{club_id}:gpu")],
        [InlineKeyboardButton(text="💰 По цене", callback_data=f"filter_cat:{club_id}:price")],
        [InlineKeyboardButton(text="🖥 По частоте (Hz)", callback_data=f"filter_cat:{club_id}:hz")],
        [InlineKeyboardButton(text="🔄 Сбросить все фильтры", callback_data=f"filter_reset:{club_id}")],
        [InlineKeyboardButton(text="« Назад к списку", callback_data=f"book:{club_id}")] # Using book: prefix to go back to list, might need adjustment if book: expects pc_id
    ]
    # Actually "book:{club_id}" usually expects pc_id, but we want to go back to computer list. 
    # In handlers/clubs.py, showing computer list is triggered by "club:{club_id}" usually? 
    # Let's check handlers. "club:{club_id}" shows club details. 
    # We want to show computer list. That is usually triggered by "computers:{club_id}" or similar?
    # Checking handlers/clubs.py... show_computers_list is triggered by "computers:{club_id}"
    
    # Correcting back button to "view_pcs:{club_id}" to match handlers/clubs.py
    buttons[-1] = [InlineKeyboardButton(text="« Назад к списку", callback_data=f"view_pcs:{club_id}")]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_filter_zone_keyboard(club_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="⭐ Standard", callback_data=f"filter_set:{club_id}:zone:Standard")],
        [InlineKeyboardButton(text="👑 VIP", callback_data=f"filter_set:{club_id}:zone:VIP")],
        [InlineKeyboardButton(text="🏆 Pro", callback_data=f"filter_set:{club_id}:zone:Pro")],
        [InlineKeyboardButton(text="✅ Любая зона", callback_data=f"filter_set:{club_id}:zone:any")],
        [InlineKeyboardButton(text="« Назад", callback_data=f"filters:{club_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_filter_gpu_keyboard(club_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="📊 GTX 1050 Ti+", callback_data=f"filter_set:{club_id}:gpu:gtx1050")],
        [InlineKeyboardButton(text="🚀 RTX 3060+", callback_data=f"filter_set:{club_id}:gpu:rtx3060")],
        [InlineKeyboardButton(text="⚡ RTX 4070+", callback_data=f"filter_set:{club_id}:gpu:rtx4070")],
        [InlineKeyboardButton(text="✅ Любая", callback_data=f"filter_set:{club_id}:gpu:any")],
        [InlineKeyboardButton(text="« Назад", callback_data=f"filters:{club_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_filter_price_keyboard(club_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="💵 До 12,000 сум", callback_data=f"filter_set:{club_id}:price:low")],
        [InlineKeyboardButton(text="💳 12,000 - 18,000 сум", callback_data=f"filter_set:{club_id}:price:mid")],
        [InlineKeyboardButton(text="💎 18,000+ сум", callback_data=f"filter_set:{club_id}:price:high")],
        [InlineKeyboardButton(text="✅ Любая цена", callback_data=f"filter_set:{club_id}:price:any")],
        [InlineKeyboardButton(text="« Назад", callback_data=f"filters:{club_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_filter_hz_keyboard(club_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="📺 60 Hz", callback_data=f"filter_set:{club_id}:hz:60")],
        [InlineKeyboardButton(text="⚡ 144 Hz", callback_data=f"filter_set:{club_id}:hz:144")],
        [InlineKeyboardButton(text="🚀 240 Hz", callback_data=f"filter_set:{club_id}:hz:240")],
        [InlineKeyboardButton(text="✅ Любая", callback_data=f"filter_set:{club_id}:hz:any")],
        [InlineKeyboardButton(text="« Назад", callback_data=f"filters:{club_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
