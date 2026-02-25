from aiogram import Router, F
from aiogram.types import CallbackQuery
from keyboards.filters import (
    get_filters_main_keyboard,
    get_filter_zone_keyboard,
    get_filter_gpu_keyboard,
    get_filter_price_keyboard,
    get_filter_hz_keyboard
)
# Removed unused import to fix circular dependency
# from handlers.clubs import show_computers_list

router = Router()

# In-memory storage for user filters
# Format: {user_id: {club_id: {'zone': 'VIP', 'gpu': 'rtx3060', ...}}}
USER_FILTERS = {}

def get_user_filters(user_id: int, club_id: int) -> dict:
    """Get active filters for user and club."""
    if user_id not in USER_FILTERS:
        USER_FILTERS[user_id] = {}
    if club_id not in USER_FILTERS[user_id]:
        USER_FILTERS[user_id][club_id] = {}
    return USER_FILTERS[user_id][club_id]

def update_user_filter(user_id: int, club_id: int, category: str, value: str):
    """Update a specific filter."""
    filters = get_user_filters(user_id, club_id)
    if value == 'any':
        if category in filters:
            del filters[category]
    else:
        filters[category] = value

@router.callback_query(F.data.startswith("filters:"))
async def show_filters_menu(callback: CallbackQuery):
    """Show main filter menu."""
    club_id = int(callback.data.split(":")[1])
    await callback.message.edit_text(
        "🔍 <b>Фильтры поиска ПК</b>\n\n"
        "Выберите категорию фильтра:",
        reply_markup=get_filters_main_keyboard(club_id),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("filter_cat:"))
async def show_filter_category(callback: CallbackQuery):
    """Show specific filter category options."""
    parts = callback.data.split(":")
    club_id = int(parts[1])
    category = parts[2]
    
    text = ""
    keyboard = None
    
    if category == "zone":
        text = "💎 <b>Фильтр по зоне:</b>"
        keyboard = get_filter_zone_keyboard(club_id)
    elif category == "gpu":
        text = "🎮 <b>Фильтр по видеокарте:</b>"
        keyboard = get_filter_gpu_keyboard(club_id)
    elif category == "price":
        text = "💰 <b>Фильтр по цене (за час):</b>"
        keyboard = get_filter_price_keyboard(club_id)
    elif category == "hz":
        text = "🖥 <b>Частота монитора:</b>"
        keyboard = get_filter_hz_keyboard(club_id)
        
    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("filter_set:"))
async def set_filter(callback: CallbackQuery):
    """Set a filter value."""
    parts = callback.data.split(":")
    club_id = int(parts[1])
    category = parts[2]
    value = parts[3]
    
    update_user_filter(callback.from_user.id, club_id, category, value)
    
    # Show confirmation or return to main menu
    # For better UX, let's go back to main filter menu so they can set more filters
    await callback.answer("✅ Фильтр применен!")
    await show_filters_menu(callback)

@router.callback_query(F.data.startswith("filter_reset:"))
async def reset_filters(callback: CallbackQuery):
    """Reset all filters for this club."""
    club_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    
    if user_id in USER_FILTERS and club_id in USER_FILTERS[user_id]:
        del USER_FILTERS[user_id][club_id]
        
    await callback.answer("🔄 Фильтры сброшены!")
    await show_filters_menu(callback)
