"""
Club Settings FSM handler for admin.
Allows club admins to update their club's: description, working_hours,
image_url, wifi_speed, and their own Telegram ID for notifications.
Accessible via /admin → Клубы → [Клуб] → ⚙️ Настройки
"""
from aiogram import Router, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select
from database import async_session_factory
from models import Club
from utils.logging import get_logger

logger = get_logger(__name__)
router = Router()


class ClubSettingsStates(StatesGroup):
    choosing_field = State()
    editing_description = State()
    editing_hours = State()
    editing_image = State()
    editing_wifi = State()
    editing_admin_tg = State()


def club_settings_keyboard(club_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Описание клуба", callback_data=f"cs_edit:description:{club_id}")],
        [InlineKeyboardButton(text="⏰ Часы работы", callback_data=f"cs_edit:hours:{club_id}")],
        [InlineKeyboardButton(text="🖼 Фото клуба (URL)", callback_data=f"cs_edit:image:{club_id}")],
        [InlineKeyboardButton(text="📶 Wi-Fi скорость", callback_data=f"cs_edit:wifi:{club_id}")],
        [InlineKeyboardButton(text="🔔 Мой TG ID для уведомлений", callback_data=f"cs_edit:admin_tg:{club_id}")],
        [InlineKeyboardButton(text="« Назад к клубу", callback_data=f"admin_club_detail:{club_id}")],
    ])


@router.callback_query(F.data.startswith("admin_club_settings:"))
async def show_club_settings(callback: CallbackQuery):
    """Show the club settings menu."""
    club_id = int(callback.data.split(":")[1])
    async with async_session_factory() as session:
        club = await session.get(Club, club_id)
    if not club:
        await callback.answer("Клуб не найден", show_alert=True)
        return

    text = (
        f"⚙️ <b>Настройки клуба: {club.name}</b>\n\n"
        f"📝 Описание: {club.description or '—'}\n"
        f"⏰ Часы: {club.working_hours or '24/7'}\n"
        f"📶 Wi-Fi: {club.wifi_speed or '—'}\n"
        f"🔔 Admin TG IDs: {club.club_admin_tg_ids or '—'}"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=club_settings_keyboard(club_id))


@router.callback_query(F.data.startswith("cs_edit:"))
async def club_settings_start_edit(callback: CallbackQuery, state: FSMContext):
    """Start editing a specific field."""
    _, field, club_id_str = callback.data.split(":")
    club_id = int(club_id_str)
    await state.update_data(cs_club_id=club_id, cs_field=field)

    prompts = {
        'description': "📝 Введите новое описание клуба (до 500 символов):",
        'hours': "⏰ Введите часы работы (например: <code>10:00–23:00</code>):",
        'image': "🖼 Введите прямую ссылку на фото клуба (URL):",
        'wifi': "📶 Введите скорость Wi-Fi (например: <code>500 Mbps</code>):",
        'admin_tg': (
            "🔔 Введите ваш Telegram ID.\n\n"
            "Узнать свой ID можно у @userinfobot.\n"
            "Можно ввести несколько через запятую: <code>123456, 789012</code>"
        ),
    }
    states_map = {
        'description': ClubSettingsStates.editing_description,
        'hours': ClubSettingsStates.editing_hours,
        'image': ClubSettingsStates.editing_image,
        'wifi': ClubSettingsStates.editing_wifi,
        'admin_tg': ClubSettingsStates.editing_admin_tg,
    }

    await callback.message.edit_text(prompts.get(field, "Введите значение:"), parse_mode="HTML")
    await state.set_state(states_map[field])


async def _save_club_field(message: Message, state: FSMContext, field: str, value: str):
    """Generic: save club field and show confirmation."""
    data = await state.get_data()
    club_id = data.get('cs_club_id')
    await state.clear()

    async with async_session_factory() as session:
        async with session.begin():
            club = await session.get(Club, club_id)
            if not club:
                await message.answer("❌ Клуб не найден.")
                return
            setattr(club, field, value)

    field_names = {
        'description': 'Описание',
        'working_hours': 'Часы работы',
        'image_url': 'Фото',
        'wifi_speed': 'Wi-Fi',
        'club_admin_tg_ids': 'TG IDs для уведомлений',
    }
    await message.answer(
        f"✅ <b>{field_names.get(field, field)}</b> обновлено!\n\n"
        f"Значение: <code>{value}</code>",
        parse_mode="HTML",
        reply_markup=club_settings_keyboard(club_id)
    )


@router.message(ClubSettingsStates.editing_description)
async def save_description(message: Message, state: FSMContext):
    await _save_club_field(message, state, 'description', message.text[:500])


@router.message(ClubSettingsStates.editing_hours)
async def save_hours(message: Message, state: FSMContext):
    await _save_club_field(message, state, 'working_hours', message.text[:100])


@router.message(ClubSettingsStates.editing_image)
async def save_image(message: Message, state: FSMContext):
    await _save_club_field(message, state, 'image_url', message.text.strip())


@router.message(ClubSettingsStates.editing_wifi)
async def save_wifi(message: Message, state: FSMContext):
    await _save_club_field(message, state, 'wifi_speed', message.text[:50])


@router.message(ClubSettingsStates.editing_admin_tg)
async def save_admin_tg(message: Message, state: FSMContext):
    # Clean up - keep only numbers and commas
    raw = message.text.strip()
    # Validate each ID is numeric
    parts = [p.strip() for p in raw.split(',') if p.strip().isdigit()]
    value = ','.join(parts)
    if not value:
        await message.answer("❌ Неверный формат. Введите числовые ID через запятую.")
        return
    await _save_club_field(message, state, 'club_admin_tg_ids', value)
