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
    from datetime import datetime, timedelta
    from utils.timezone import now_tashkent, TASHKENT_TZ
    from sqlalchemy import and_, desc
    from models import Computer, Review

    async with async_session_factory() as session:
        now = now_tashkent()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=7)

        # --- Basic counts ---
        users_count = await session.scalar(select(func.count(User.id)))
        clubs_count = await session.scalar(select(func.count(Club.id)))
        bookings_total = await session.scalar(select(func.count(Booking.id)))
        active_now = await session.scalar(
            select(func.count(Booking.id)).where(Booking.status == "ACTIVE")
        )

        # --- Today ---
        today_bookings = await session.scalar(
            select(func.count(Booking.id)).where(Booking.created_at >= today_start)
        )

        # --- This week ---
        week_bookings = await session.scalar(
            select(func.count(Booking.id)).where(Booking.created_at >= week_start)
        )

        # --- Weekly Revenue — Single JOIN query (no N+1) ---
        from sqlalchemy import case
        week_revenue_result = await session.execute(
            select(
                func.sum(
                    Computer.price_per_hour * (
                        func.julianday(Booking.end_time) - func.julianday(Booking.start_time)
                    ) * 24
                ).label("revenue")
            )
            .select_from(Booking)
            .join(Computer, Booking.item_id == Computer.id, isouter=True)
            .where(
                and_(
                    Booking.created_at >= week_start,
                    Booking.status.in_(["COMPLETED", "ACTIVE", "CONFIRMED"]),
                    Computer.price_per_hour.isnot(None)
                )
            )
        )
        revenue = int(week_revenue_result.scalar() or 0)

        # --- Reviews ---
        reviews_count = await session.scalar(select(func.count(Review.id)))
        avg_rating_result = await session.scalar(select(func.avg(Review.rating)))
        avg_rating = f"{avg_rating_result:.1f}" if avg_rating_result else "—"

        # --- Top 3 PCs by booking count ---
        top_pcs_result = await session.execute(
            select(Booking.computer_name, func.count(Booking.id).label("cnt"))
            .group_by(Booking.computer_name)
            .order_by(desc("cnt"))
            .limit(3)
        )
        top_pcs = top_pcs_result.all()
        top_pcs_text = "\n".join(
            [f"  {i+1}. {row.computer_name} — {row.cnt} броней" for i, row in enumerate(top_pcs)]
        ) or "  Нет данных"

        # --- Per-Club daily revenue — Single JOIN query per club (much better than N+1) ---
        per_club_result = await session.execute(
            select(
                Club.id,
                Club.name,
                func.count(Booking.id).label("today_count"),
                func.sum(
                    Computer.price_per_hour * (
                        func.julianday(Booking.end_time) - func.julianday(Booking.start_time)
                    ) * 24
                ).label("today_revenue")
            )
            .select_from(Club)
            .outerjoin(
                Booking,
                and_(
                    Booking.club_id == Club.id,
                    Booking.created_at >= today_start,
                    Booking.status.in_(["CONFIRMED", "ACTIVE", "COMPLETED"])
                )
            )
            .outerjoin(Computer, Booking.item_id == Computer.id)
            .where(Club.is_active == True)
            .group_by(Club.id, Club.name)
        )
        per_club_rows = per_club_result.all()

        per_club_lines = []
        for row in per_club_rows:
            rev = int(row.today_revenue or 0)
            cnt = row.today_count or 0
            line = f"  🏢 <b>{row.name}</b>: {cnt} броней"
            if rev > 0:
                line += f" (~{rev:,} сум)"
            per_club_lines.append(line)

        per_club_text = "\n".join(per_club_lines) if per_club_lines else "  Нет клубов"


    text = (
        f"📊 <b>Статистика платформы</b>\n\n"
        f"👥 Пользователей: <b>{users_count}</b>\n"
        f"🏢 Клубов: <b>{clubs_count}</b>\n"
        f"🟢 Активных сеансов: <b>{active_now}</b>\n\n"
        f"📅 <b>Брони сегодня:</b> {today_bookings}  |  <b>За неделю:</b> {week_bookings}\n"
        f"📝 Всего броней: {bookings_total}\n\n"
        f"💰 <b>Выручка за неделю:</b> ~{revenue:,} сум\n\n"
        f"⭐ <b>Отзывы:</b> {reviews_count} (средний: {avg_rating})\n\n"
        f"🏆 <b>Популярные места:</b>\n{top_pcs_text}\n\n"
        f"📊 <b>Брони сегодня по клубам:</b>\n{per_club_text}"
    )

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_stats"),
        InlineKeyboardButton(text="« Назад", callback_data="admin_back_main")
    ]])
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

class BroadcastStates(StatesGroup):
    waiting_for_message = State()
    waiting_for_confirm = State()

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext):
    """Start broadcast feature."""
    await callback.message.edit_text(
        "📢 <b>Рассылка сообщений</b>\n\n"
        "Отправьте сообщение, которое хотите разослать всем пользователям бота.\n"
        "Вы можете отправить текст, фото или видео (с подписью).",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Клубы", callback_data="admin_clubs")]]) # generic cancel back to menu
    )
    await state.set_state(BroadcastStates.waiting_for_message)

@router.message(BroadcastStates.waiting_for_message)
async def admin_broadcast_preview(message: Message, state: FSMContext):
    await state.update_data(broadcast_msg_id=message.message_id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Отправить всем", callback_data="broadcast_confirm")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_clubs")]
    ])
    await message.copy_to(message.chat.id, reply_markup=kb)
    await message.answer("👆 Так выглядит ваше сообщение. Начать рассылку?")
    await state.set_state(BroadcastStates.waiting_for_confirm)

@router.callback_query(BroadcastStates.waiting_for_confirm, F.data == "broadcast_confirm")
async def admin_broadcast_send(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    msg_id = data.get("broadcast_msg_id")
    await state.clear()
    
    await callback.message.edit_text("⏳ Рассылка началась. Это может занять некоторое время...")
    
    async with async_session_factory() as session:
        result = await session.execute(select(User.telegram_id))
        users = result.scalars().all()
        
    success = 0
    from aiogram import Bot
    from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
    bot: Bot = callback.bot
    
    for tg_id in users:
        try:
            await bot.copy_message(chat_id=tg_id, from_chat_id=callback.message.chat.id, message_id=msg_id)
            success += 1
            import asyncio
            await asyncio.sleep(0.05) # Prevent flood wait
        except (TelegramForbiddenError, TelegramBadRequest):
            pass # User blocked the bot or chat not found
            
    await callback.message.edit_text(f"✅ Рассылка завершена!\nУспешно отправлено: <b>{success}</b> пользователям.", parse_mode="HTML")

from keyboards.admin import get_club_settings_menu

class ClubSettingsStates(StatesGroup):
    waiting_for_desc = State()
    waiting_for_hours = State()
    waiting_for_photo = State()
    waiting_for_wifi = State()

@router.callback_query(F.data.startswith("admin_club_settings:"))
async def admin_club_settings(callback: CallbackQuery):
    """Show club settings menu."""
    club_id = int(callback.data.split(":")[1])
    async with async_session_factory() as session:
        club = await session.get(Club, club_id)
        if not club:
            await callback.answer("Клуб не найден!", show_alert=True)
            return
            
        text = (
            f"⚙️ <b>Настройки: {club.name}</b>\n\n"
            f"📝 <b>Описание:</b> {club.description or 'Нет'}\n"
            f"🕒 <b>Часы работы:</b> {club.working_hours or 'Нет'}\n"
            f"📸 <b>Фото:</b> {'Установлено' if club.image_url else 'Нет'}\n"
            f"📶 <b>Wi-Fi:</b> {club.wifi_info or 'Нет'}"
        )
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_club_settings_menu(club_id))

@router.callback_query(F.data.startswith("edit_club_"))
async def start_edit_club_field(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    action = parts[0]
    club_id = int(parts[1])
    
    await state.update_data(edit_club_id=club_id)
    
    if action == "edit_club_desc":
        await callback.message.edit_text("Отправьте новое описание для клуба:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data=f"admin_club_settings:{club_id}")]]))
        await state.set_state(ClubSettingsStates.waiting_for_desc)
    elif action == "edit_club_hours":
        await callback.message.edit_text("Отправьте часы работы (например: 10:00 - 22:00 или 24/7):", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data=f"admin_club_settings:{club_id}")]]))
        await state.set_state(ClubSettingsStates.waiting_for_hours)
    elif action == "edit_club_photo":
        await callback.message.edit_text("Отправьте прямую ссылку на фото (URL) клуба:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data=f"admin_club_settings:{club_id}")]]))
        await state.set_state(ClubSettingsStates.waiting_for_photo)
    elif action == "edit_club_wifi":
        await callback.message.edit_text("Отправьте название и пароль Wi-Fi (например: MyClub / password):", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data=f"admin_club_settings:{club_id}")]]))
        await state.set_state(ClubSettingsStates.waiting_for_wifi)

async def _save_club_field(message: Message, state: FSMContext, field: str, value: str):
    data = await state.get_data()
    club_id = data.get("edit_club_id")
    await state.clear()
    
    async with async_session_factory() as session:
        async with session.begin():
            club = await session.get(Club, club_id)
            if club:
                setattr(club, field, value)
                
    await dict(message=message, club_id=club_id)
    await message.answer(f"✅ Успешно обновлено!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Вернуться к настройкам", callback_data=f"admin_club_settings:{club_id}")]]))

@router.message(ClubSettingsStates.waiting_for_desc)
async def save_club_desc(message: Message, state: FSMContext):
    await _save_club_field(message, state, "description", message.text.strip())

@router.message(ClubSettingsStates.waiting_for_hours)
async def save_club_hours(message: Message, state: FSMContext):
    await _save_club_field(message, state, "working_hours", message.text.strip())

@router.message(ClubSettingsStates.waiting_for_photo)
async def save_club_photo(message: Message, state: FSMContext):
    url = message.text.strip()
    if not url.startswith("http"):
        await message.answer("❌ Ссылка должна начинаться с http или https. Попробуйте еще раз.")
        return
    await _save_club_field(message, state, "image_url", url)

@router.message(ClubSettingsStates.waiting_for_wifi)
async def save_club_wifi(message: Message, state: FSMContext):
    await _save_club_field(message, state, "wifi_info", message.text.strip())


# --- View/Delete Individual Item (PC or Table) ---
@router.callback_query(F.data.startswith("admin_item_view:"))
async def admin_item_view(callback: CallbackQuery):
    """View details of a specific computer or restaurant table."""
    parts = callback.data.split(":")
    item_id = int(parts[1])
    venue_type = parts[2] if len(parts) > 2 else "computer_club"
    
    async with async_session_factory() as session:
        if venue_type == "restaurant":
            item = await session.get(RestaurantTable, item_id)
            if not item:
                await callback.answer("❌ Стол не найден", show_alert=True)
                return
            
            text = (
                f"🍽 <b>{item.name}</b>\n\n"
                f"📍 Зона: {item.zone}\n"
                f"👥 Мест: {item.seats}\n"
                f"💰 Депозит: {item.min_deposit} сум\n"
                f"🔑 Цена брони: {item.booking_price} сум\n"
                f"📸 Фото: {'✅' if item.image_url else '❌'}\n"
                f"⚡ Статус: {'✅ Активен' if item.is_active else '❌ Неактивен'}"
            )
            club_id = item.club_id
        else:
            item = await session.get(Computer, item_id)
            if not item:
                await callback.answer("❌ Компьютер не найден", show_alert=True)
                return
            
            text = (
                f"💻 <b>{item.name}</b>\n\n"
                f"📍 Зона: {item.zone}\n"
                f"🖥 CPU: {item.cpu or 'Не указан'}\n"
                f"🎮 GPU: {item.gpu or 'Не указана'}\n"
                f"🧠 RAM: {item.ram_gb or '?'} GB\n"
                f"📺 Монитор: {item.monitor_hz or '?'} Hz\n"
                f"💰 Цена: {item.price_per_hour or 0} сум/ч\n"
                f"📸 Фото: {'✅' if item.image_url else '❌'}\n"
                f"⚡ Статус: {'✅ Активен' if item.is_active else '❌ Неактивен'}"
            )
            club_id = item.club_id
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🔄 Вкл/Выкл" , 
            callback_data=f"admin_toggle_item:{item_id}:{venue_type}"
        )],
        [InlineKeyboardButton(
            text="🗑 Удалить", 
            callback_data=f"admin_delete_item:{item_id}:{venue_type}"
        )],
        [InlineKeyboardButton(
            text="« Назад", 
            callback_data=f"admin_club_computers:{club_id}"
        )]
    ])
    
    await safe_edit(callback.message, text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("admin_toggle_item:"))
async def admin_toggle_item(callback: CallbackQuery):
    """Toggle active/inactive status of an item."""
    parts = callback.data.split(":")
    item_id = int(parts[1])
    venue_type = parts[2] if len(parts) > 2 else "computer_club"
    
    async with async_session_factory() as session:
        if venue_type == "restaurant":
            item = await session.get(RestaurantTable, item_id)
        else:
            item = await session.get(Computer, item_id)
        
        if not item:
            await callback.answer("❌ Объект не найден", show_alert=True)
            return
        
        item.is_active = not item.is_active
        new_status = "✅ Активен" if item.is_active else "❌ Неактивен"
        await session.commit()
    
    await callback.answer(f"Статус изменён: {new_status}", show_alert=True)
    
    # Refresh the item view
    callback.data = f"admin_item_view:{item_id}:{venue_type}"
    await admin_item_view(callback)


@router.callback_query(F.data.startswith("admin_delete_item:"))
async def admin_delete_item(callback: CallbackQuery):
    """Delete a specific computer or table."""
    parts = callback.data.split(":")
    item_id = int(parts[1])
    venue_type = parts[2] if len(parts) > 2 else "computer_club"
    
    async with async_session_factory() as session:
        if venue_type == "restaurant":
            item = await session.get(RestaurantTable, item_id)
        else:
            item = await session.get(Computer, item_id)
        
        if not item:
            await callback.answer("❌ Объект не найден", show_alert=True)
            return
        
        club_id = item.club_id
        item_name = item.name
        await session.delete(item)
        await session.commit()
    
    await callback.answer(f"✅ {item_name} удалён", show_alert=True)
    
    # Return to items list
    callback.data = f"admin_club_computers:{club_id}"
    await show_computers_list(callback)

