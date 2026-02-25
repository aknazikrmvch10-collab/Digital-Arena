from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, func

from config import settings
from utils.telegram_helpers import safe_edit, safe_delete
from database import async_session_factory
from models import User, Club, Booking, Computer, RestaurantTable
from keyboards.admin import (
    get_admin_main_menu, 
    get_admin_clubs_menu, 
    get_driver_type_keyboard,
    get_club_detail_menu,
    get_computers_list_menu,
    get_zone_selection_keyboard,
    get_venue_type_keyboard
)
from drivers.factory import DriverFactory

router = Router()

# FSM for adding a club
class AddClubStates(StatesGroup):
    waiting_for_venue_type = State()
    waiting_for_name = State()
    waiting_for_city = State()
    waiting_for_address = State()
    waiting_for_driver = State()

# FSM for adding a computer
class AddItemStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_zone = State()
    # Computer specific
    waiting_for_cpu = State()
    waiting_for_gpu = State()
    waiting_for_ram = State()
    waiting_for_monitor = State()
    waiting_for_price = State()
    # Table specific
    waiting_for_seats = State()
    waiting_for_min_deposit = State()

# --- Admin Filter ---
async def is_admin(user_id: int) -> bool:
    # Check DB for super admin
    async with async_session_factory() as session:
        from models import Admin
        result = await session.execute(select(Admin).where(Admin.tg_id == user_id))
        admin = result.scalars().first()
        return admin is not None

# --- Main Admin Menu ---
@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not await is_admin(message.from_user.id):
        return # Ignore non-admins
        
    await message.answer(
        "🛠 <b>Админ-панель</b>\n\nВыберите действие:",
        reply_markup=get_admin_main_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "admin_back_main")
async def back_to_admin(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await safe_edit(
        callback.message,
        "🛠 <b>Админ-панель</b>\n\nВыберите действие:",
        reply_markup=get_admin_main_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "admin_close")
async def close_admin(callback: CallbackQuery):
    await safe_delete(callback.message)

# --- Statistics ---
@router.callback_query(F.data == "admin_stats")
async def show_stats(callback: CallbackQuery):
    async with async_session_factory() as session:
        users_count = await session.scalar(select(func.count(User.id)))
        clubs_count = await session.scalar(select(func.count(Club.id)))
        bookings_count = await session.scalar(select(func.count(Booking.id)))
        
        # Active bookings
        active_bookings = await session.scalar(
            select(func.count(Booking.id)).where(Booking.status == "ACTIVE")
        )

    text = (
        "📊 <b>Статистика бота</b>\n\n"
        f"👥 Пользователей: {users_count}\n"
        f"🏢 Клубов: {clubs_count}\n"
        f"📝 Всего броней: {bookings_count}\n"
        f"🟢 Сейчас играют: {active_bookings}"
    )
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Назад", callback_data="admin_back_main")]])
    
    await safe_edit(callback.message, text, reply_markup=back_kb, parse_mode="HTML")

# --- Club Management ---
@router.callback_query(F.data == "admin_clubs")
async def show_clubs(callback: CallbackQuery):
    async with async_session_factory() as session:
        result = await session.execute(select(Club))
        clubs = result.scalars().all()
        
    await safe_edit(callback.message,
        "🏢 <b>Управление клубами</b>\n\nВыберите клуб или добавьте новый:",
        reply_markup=get_admin_clubs_menu(clubs),
        parse_mode="HTML"
    )

# --- Add Club Wizard ---
@router.callback_query(F.data == "admin_add_club")
async def start_add_club(callback: CallbackQuery, state: FSMContext):
    await safe_edit(
        callback.message, 
        "Выберите <b>тип заведения</b>:",
        reply_markup=get_venue_type_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(AddClubStates.waiting_for_venue_type)

@router.callback_query(AddClubStates.waiting_for_venue_type)
async def process_venue_type(callback: CallbackQuery, state: FSMContext):
    venue_type = callback.data.split(":")[1]
    await state.update_data(venue_type=venue_type)
    await safe_edit(callback.message, "Введите <b>название</b> (например: CyberZone, Bella Napoli):", parse_mode="HTML")
    await state.set_state(AddClubStates.waiting_for_name)

@router.message(AddClubStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите <b>город</b>:")
    await state.set_state(AddClubStates.waiting_for_city)

@router.message(AddClubStates.waiting_for_city)
async def process_city(message: Message, state: FSMContext):
    await state.update_data(city=message.text)
    await message.answer("Введите <b>адрес</b>:")
    await state.set_state(AddClubStates.waiting_for_address)

@router.message(AddClubStates.waiting_for_address)
async def process_address(message: Message, state: FSMContext):
    await state.update_data(address=message.text)
    data = await state.get_data()
    venue_type = data.get('venue_type', 'computer_club')
    
    # If restaurant, we might skip driver selection or use MOCK by default for now?
    # Or just let them pick MOCK/STANDALONE.
    # Restaurants usually don't use 'SmartShell'.
    # Let's show Driver Menu anyway but maybe simplified? For now, standard is fine.
    
    await message.answer(
        "Выберите <b>тип драйвера</b> (систему управления):",
        reply_markup=get_driver_type_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(AddClubStates.waiting_for_driver)

@router.callback_query(AddClubStates.waiting_for_driver)
async def process_driver(callback: CallbackQuery, state: FSMContext):
    driver_type = callback.data.split(":")[1]
    data = await state.get_data()
    
    async with async_session_factory() as session:
        new_club = Club(
            name=data['name'],
            city=data['city'],
            address=data['address'],
            venue_type=data['venue_type'], # Added
            driver_type=driver_type,
            connection_config={}, # Empty config for now
            is_active=True
        )
        session.add(new_club)
        await session.commit()
    
    await state.clear()
    await safe_edit(
        callback.message,
        f"✅ <b>Клуб {data['name']} успешно добавлен!</b>",
        reply_markup=get_admin_main_menu(),
        parse_mode="HTML"
    )

# --- Club Details ---
@router.callback_query(F.data.startswith("admin_club:"))
async def show_club_detail(callback: CallbackQuery):
    club_id = int(callback.data.split(":")[1])
    
    async with async_session_factory() as session:
        result = await session.execute(select(Club).where(Club.id == club_id))
        club = result.scalars().first()
        
        if not club:
            await callback.answer("Клуб не найден", show_alert=True)
            return
        
        venue_type = getattr(club, 'venue_type', 'computer_club')
        
        if venue_type == 'restaurant':
             items_count = await session.scalar(
                select(func.count(RestaurantTable.id)).where(RestaurantTable.club_id == club_id)
            )
             items_label = "Столов"
        else:
            items_count = await session.scalar(
                select(func.count(Computer.id)).where(Computer.club_id == club_id)
            )
            items_label = "Компьютеров"
    
    text = (
        f"🏢 <b>{club.name}</b>\n\n"
        f"📍 Город: {club.city}\n"
        f"🗺 Адрес: {club.address}\n"
        f"🏷 Тип: {venue_type}\n"
        f"🖥 Драйвер: {club.driver_type}\n"
        f"📦 {items_label}: {items_count}\n"
    )
    
    await safe_edit(callback.message, text, reply_markup=get_club_detail_menu(club_id, venue_type), parse_mode="HTML")

# --- Computers List ---
@router.callback_query(F.data.startswith("admin_club_computers:"))
async def show_computers_list(callback: CallbackQuery):
    club_id = int(callback.data.split(":")[1])
    
    async with async_session_factory() as session:
        club_result = await session.execute(select(Club).where(Club.id == club_id))
        club = club_result.scalars().first()
        
        venue_type = getattr(club, 'venue_type', 'computer_club')
        
        items = []
        if venue_type == 'restaurant':
            # Restaurants use local DB tables
            item_result = await session.execute(select(RestaurantTable).where(RestaurantTable.club_id == club_id))
            items = item_result.scalars().all()
        else:
            # Computers might use driver
            # Use driver to get computers
            try:
                driver = DriverFactory.get_driver(club.driver_type, {"club_id": club.id, **club.connection_config})
                items = await driver.get_computers()
            except Exception as e:
                print(f"Driver error: {e}")
                items = []
    
    if not items:
        text = f"📦 <b>Объекты заведения {club.name}</b>\n\nСписок пуст."
    else:
        text = f"📦 <b>Объекты заведения {club.name}</b>\n\nВсего: {len(items)}"
    
    await safe_edit(callback.message, text, reply_markup=get_computers_list_menu(club_id, items, venue_type), parse_mode="HTML")

# --- Add Item (Computer/Table) Wizard ---
@router.callback_query(F.data.startswith("admin_add_computer:"))
async def start_add_item(callback: CallbackQuery, state: FSMContext):
    club_id = int(callback.data.split(":")[1])
    
    # Get club type
    async with async_session_factory() as session:
        club = await session.get(Club, club_id)
        venue_type = getattr(club, 'venue_type', 'computer_club')
    
    await state.update_data(club_id=club_id, venue_type=venue_type)
    
    prompt = "Введите <b>название стола</b> (например: Стол 1, Кабинка 5):" if venue_type == 'restaurant' else "Введите <b>название компьютера</b> (например: PC-1, VIP-5):"
    
    await safe_edit(callback.message, prompt, parse_mode="HTML")
    await state.set_state(AddItemStates.waiting_for_name)

@router.message(AddItemStates.waiting_for_name)
async def process_item_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    
    data = await state.get_data()
    venue_type = data.get('venue_type', 'computer_club')
    
    await message.answer(
        "Выберите <b>зону</b>:",
        reply_markup=get_zone_selection_keyboard(venue_type),
        parse_mode="HTML"
    )
    await state.set_state(AddItemStates.waiting_for_zone)

@router.callback_query(AddItemStates.waiting_for_zone)
async def process_item_zone(callback: CallbackQuery, state: FSMContext):
    zone = callback.data.split(":")[1]
    await state.update_data(zone=zone)
    
    data = await state.get_data()
    if data.get('venue_type') == 'restaurant':
        await safe_edit(callback.message, "Введите <b>количество мест</b> (например: 4):", parse_mode="HTML")
        await state.set_state(AddItemStates.waiting_for_seats)
    else:
        await safe_edit(callback.message, "Введите <b>процессор</b> (например: Intel i5-12400):", parse_mode="HTML")
        await state.set_state(AddItemStates.waiting_for_cpu)

# --- Computer Specific Flow ---
@router.message(AddItemStates.waiting_for_cpu)
async def process_computer_cpu(message: Message, state: FSMContext):
    await state.update_data(cpu=message.text)
    await message.answer("Введите <b>видеокарту</b> (например: RTX 3060):", parse_mode="HTML")
    await state.set_state(AddItemStates.waiting_for_gpu)

@router.message(AddItemStates.waiting_for_gpu)
async def process_computer_gpu(message: Message, state: FSMContext):
    await state.update_data(gpu=message.text)
    await message.answer("Введите <b>RAM в GB</b> (например: 16):", parse_mode="HTML")
    await state.set_state(AddItemStates.waiting_for_ram)

@router.message(AddItemStates.waiting_for_ram)
async def process_computer_ram(message: Message, state: FSMContext):
    try:
        ram = int(message.text)
        await state.update_data(ram_gb=ram)
        await message.answer("Введите <b>частоту монитора в Hz</b> (например: 144):", parse_mode="HTML")
        await state.set_state(AddItemStates.waiting_for_monitor)
    except ValueError:
        await message.answer("❌ Введите число (например: 16)")

@router.message(AddItemStates.waiting_for_monitor)
async def process_computer_monitor(message: Message, state: FSMContext):
    try:
        monitor = int(message.text)
        await state.update_data(monitor_hz=monitor)
        await message.answer("Введите <b>цену за час в сумах</b> (например: 15000):", parse_mode="HTML")
        await state.set_state(AddItemStates.waiting_for_price)
    except ValueError:
        await message.answer("❌ Введите число (например: 144)")

@router.message(AddItemStates.waiting_for_price)
async def process_computer_price(message: Message, state: FSMContext):
    try:
        price = int(message.text)
        # Use common save function/logic
        await save_item(message, state, price_arg=price)
    except ValueError:
        await message.answer("❌ Введите число (например: 15000)")

# --- Restaurant Specific Flow ---
@router.message(AddItemStates.waiting_for_seats)
async def process_table_seats(message: Message, state: FSMContext):
    try:
        seats = int(message.text)
        await state.update_data(seats=seats)
        await message.answer("Введите <b>сумму депозита</b> (например: 50000) или 0:", parse_mode="HTML")
        await state.set_state(AddItemStates.waiting_for_min_deposit)
    except ValueError:
        await message.answer("❌ Введите число (например: 4)")

@router.message(AddItemStates.waiting_for_min_deposit)
async def process_table_deposit(message: Message, state: FSMContext):
    try:
        deposit = int(message.text)
        # Use common save function/logic
        await save_item(message, state, min_deposit_arg=deposit)
    except ValueError:
        await message.answer("❌ Введите число (например: 50000)")

async def save_item(message: Message, state: FSMContext, price_arg=None, min_deposit_arg=0):
    data = await state.get_data()
    venue_type = data.get('venue_type', 'computer_club')
    
    async with async_session_factory() as session:
        if venue_type == 'restaurant':
            new_item = RestaurantTable(
                club_id=data['club_id'],
                name=data['name'],
                zone=data['zone'],
                seats=data['seats'],
                min_deposit=min_deposit_arg,
                is_active=True
            )
            session.add(new_item)
            success_msg = (
                f"✅ <b>Стол {data['name']} успешно добавлен!</b>\n\n"
                f"Зона: {data['zone']}\n"
                f"Мест: {data['seats']}\n"
                f"Депозит: {min_deposit_arg} сум"
            )
        else:
            new_item = Computer(
                club_id=data['club_id'],
                name=data['name'],
                zone=data['zone'],
                cpu=data['cpu'],
                gpu=data['gpu'],
                ram_gb=data['ram_gb'],
                monitor_hz=data['monitor_hz'],
                price_per_hour=price_arg,
                is_active=True
            )
            session.add(new_item)
            success_msg = (
                f"✅ <b>Компьютер {data['name']} успешно добавлен!</b>\n\n"
                f"Зона: {data['zone']}\n"
                f"CPU: {data['cpu']}\n"
                f"GPU: {data['gpu']}\n"
                f"RAM: {data['ram_gb']} GB\n"
                f"Монитор: {data['monitor_hz']} Hz\n"
                f"Цена: {price_arg} сум/ч"
            )
        
        await session.commit()
    
    await state.clear()
    await message.answer(
        success_msg,
        reply_markup=get_admin_main_menu(),
        parse_mode="HTML"
    )

# --- Delete Club ---
@router.callback_query(F.data.startswith("admin_delete_club:"))
async def confirm_delete_club(callback: CallbackQuery):
    """Ask for confirmation before deleting club."""
    club_id = int(callback.data.split(":")[1])
    
    async with async_session_factory() as session:
        club = await session.get(Club, club_id)
        if not club:
            await callback.answer("❌ Клуб не найден", show_alert=True)
            return
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"admin_confirm_delete:{club_id}")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"admin_club:{club_id}")]
        ])
        
        await safe_edit(
            callback.message,
            f"⚠️ <b>Удаление клуба</b>\n\n"
            f"Вы уверены, что хотите удалить клуб <b>{club.name}</b>?\n\n"
            f"<i>Это действие нельзя отменить!</i>",
            reply_markup=keyboard,
            parse_mode="HTML"
        )

@router.callback_query(F.data.startswith("admin_confirm_delete:"))
async def delete_club(callback: CallbackQuery):
    """Delete the club from database."""
    club_id = int(callback.data.split(":")[1])
    
    async with async_session_factory() as session:
        club = await session.get(Club, club_id)
        if not club:
            await callback.answer("❌ Клуб не найден", show_alert=True)
            return
        
        club_name = club.name
        
        # Delete all computers for this club
        computers_result = await session.execute(
            select(Computer).where(Computer.club_id == club_id)
        )
        computers = computers_result.scalars().all()
        for computer in computers:
            await session.delete(computer)
            
        # Delete all tables for this club
        tables_result = await session.execute(
            select(RestaurantTable).where(RestaurantTable.club_id == club_id)
        )
        tables = tables_result.scalars().all()
        for table in tables:
            await session.delete(table)
        
        # Delete all bookings for this club
        bookings_result = await session.execute(
            select(Booking).where(Booking.club_id == club_id)
        )
        bookings = bookings_result.scalars().all()
        for booking in bookings:
            await session.delete(booking)
        
        # Delete the club
        await session.delete(club)
        await session.commit()
    
    await callback.answer(f"✅ Клуб {club_name} удален", show_alert=True)
    
    # Show updated clubs list
    async with async_session_factory() as session:
        result = await session.execute(select(Club))
        clubs = result.scalars().all()
    
    await safe_edit(
        callback.message,
        "🏢 <b>Управление клубами</b>\n\nВыберите клуб для управления:",
        reply_markup=get_admin_clubs_menu(clubs),
        parse_mode="HTML"
    )

# --- Placeholder handlers ---
@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback: CallbackQuery):
    """Placeholder for broadcast feature."""
    await callback.answer("📢 Рассылка будет доступна в следующем обновлении!", show_alert=True)

@router.callback_query(F.data.startswith("admin_club_settings:"))
async def admin_club_settings(callback: CallbackQuery):
    """Placeholder for club settings."""
    await callback.answer("⚙️ Настройки клуба будут доступны в следующем обновлении!", show_alert=True)

