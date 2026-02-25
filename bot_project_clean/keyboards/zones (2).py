from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from drivers.base import ZoneSchema

def get_zones_keyboard(club_id: int, zones: list[ZoneSchema]) -> InlineKeyboardMarkup:
    """Show available zones in the club."""
    buttons = []
    
    for zone in zones:
        # Format: "🟦 Standard | GTX 1060 | 10k"
        icon = "🟦" if zone.name == "Standard" else "🟪" if zone.name == "VIP" else "🟧"
        
        spec_info = ""
        if zone.gpu:
            spec_info = f" | {zone.gpu}"
            if zone.monitor_hz:
                spec_info += f" {zone.monitor_hz}Hz"
        
        price_k = int(zone.min_price / 1000)
        text = f"{icon} {zone.name}{spec_info} | от {price_k}k сум"
        
        buttons.append([
            InlineKeyboardButton(
                text=text,
                callback_data=f"view_zone_pcs:{club_id}:{zone.name}"
            )
        ])
    
    buttons.append([InlineKeyboardButton(text="« Назад к клубу", callback_data=f"club:{club_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
