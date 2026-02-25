from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from sqlalchemy import select, and_

from models import Club, User, Booking
from database import async_session_factory
from keyboards.main import (get_clubs_keyboard, get_club_detail_keyboard, get_computers_keyboard, 
                              get_main_menu, get_date_keyboard, get_time_keyboard,
                              get_minute_keyboard, get_duration_keyboard)

from drivers.factory import DriverFactory
from utils.telegram_helpers import safe_delete

router = Router()

@router.message(F.text == "🏢 Клубы")
@router.callback_query(F.data == "find_clubs")
async def show_clubs_list(event: Message | CallbackQuery):
    """Show all available clubs."""
    async with async_session_factory() as session:
        result = await session.execute(select(Club).where(Club.is_active == True))
        clubs = result.scalars().all()
        
        if not clubs:
            if isinstance(event, CallbackQuery):
                await event.answer("Нет доступных клубов.", show_alert=True)
            else:
                await event.answer("Нет доступных клубов.")
            return
        
        text = "🏢 <b>Доступные клубы:</b>\n\nВыберите клуб для просмотра деталей:"
        keyboard = get_clubs_keyboard(clubs)
        
        if isinstance(event, CallbackQuery):
            # Edit existing message (no duplicate)
            await event.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
            await event.answer()
        else:
            # New message from reply keyboard
            await event.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "back_main")
async def back_to_main(callback: CallbackQuery):
    """Return to main menu."""
    await safe_delete(callback.message)
    
    from keyboards.main import get_main_reply_keyboard
    await callback.message.answer(
        f"👋 <b>Главное меню</b>\n\n"
        "Выберите действие на клавиатуре ниже 👇",
        reply_markup=get_main_reply_keyboard(),
        parse_mode="HTML"
    )

@router.message(F.text == "👤 Мои брони")
@router.callback_query(F.data == "my_bookings")
async def show_my_bookings(event: Message | CallbackQuery):
    """Show user's bookings."""
    # Handle both Message and CallbackQuery
    if isinstance(event, Message):
        message = event
        user_id = event.from_user.id
    else:
        message = event.message
        user_id = event.from_user.id
        
    async with async_session_factory() as session:
        # Get user
        result = await session.execute(
            select(User).where(User.tg_id == user_id)
        )
        user = result.scalars().first()
        
        if not user:
            await message.answer("Вы не зарегистрированы.")
            return
        
        # ✅ FIX: Get bookings with eager loading to avoid N+1 query problem
        from sqlalchemy.orm import selectinload
        
        result = await session.execute(
            select(Booking)
            .options(selectinload(Booking.club))  # ✅ Eager load club relationship
            .where(Booking.user_id == user.id)
            .order_by(Booking.start_time.desc())
        )
        bookings = result.scalars().all()
        
        if not bookings:
            text = "📋 <b>Мои брони</b>\n\nУ вас пока нет бронирований."
            keyboard = get_main_menu()
        else:
            text = "📋 <b>Мои брони</b>\n\n"
            buttons = []
            
            for b in bookings:
                # ✅ FIX: Club is already loaded, no extra query needed
                club = b.club  # No database query here!
                
                # Status emoji and description
                if b.status == "CONFIRMED":
                    status_emoji = "🟡"
                    status_text = "Ожидает"
                elif b.status == "ACTIVE":
                    status_emoji = "🟢"
                    status_text = "Играет"
                elif b.status == "COMPLETED":
                    status_emoji = "✅"
                    status_text = "Завершено"
                elif b.status == "NO_SHOW":
                    status_emoji = "❌"
                    status_text = "Не пришел"
                elif b.status == "CANCELLED":
                    status_emoji = "❌"
                    status_text = "Отменено"
                else:
                    status_emoji = "⏳"
                    status_text = b.status
                
                from datetime import timezone, timedelta
                tz = timezone(timedelta(hours=5))
                text += f"{status_emoji} <b>{b.computer_name}</b> в {club.name}\n"
                text += f"  {b.start_time.astimezone(tz).strftime('%d.%m %H:%M')} - {b.end_time.astimezone(tz).strftime('%H:%M')}\n"
                text += f"  Статус: {status_text}\n\n"
                
                # Add cancel button only for CONFIRMED bookings
                if b.status == "CONFIRMED":
                    from aiogram.types import InlineKeyboardButton
                    buttons.append([
                        InlineKeyboardButton(
                            text=f"❌ Отменить {b.computer_name} ({b.start_time.astimezone(tz).strftime('%d.%m %H:%M')})",
                            callback_data=f"cancel_booking:{b.id}"
                        )
                    ])
            
            # Add clear history button if there are any completed/cancelled bookings
            has_old_bookings = any(b.status in ["COMPLETED", "CANCELLED", "NO_SHOW"] for b in bookings)
            if has_old_bookings:
                from aiogram.types import InlineKeyboardButton
                buttons.append([InlineKeyboardButton(text="🗑 Очистить историю", callback_data="clear_history")])
            
            # Add back button
            from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
            buttons.append([InlineKeyboardButton(text="« Назад", callback_data="back_main")])
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await message.answer(
            text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )

@router.message(Command("help"))
@router.message(F.text == "🆘 Помощь")
@router.callback_query(F.data == "about")
async def show_about(event: Message | CallbackQuery):
    """Show about info."""
    if isinstance(event, Message):
        message = event
    else:
        message = event.message

    await message.answer(
        "🆘 <b>Центр помощи</b>\n\n"
        "Я помогу вам забронировать компьютер в любимом клубе.\n\n"
        "<b>Как пользоваться:</b>\n"
        "1. Нажмите <b>🏢 Клубы</b>, чтобы выбрать клуб.\n"
        "2. Выберите зону и компьютер.\n"
        "3. Укажите время и длительность.\n"
        "4. Готово! Компьютер забронирован.\n\n"
        "📞 <b>Техподдержка:</b>\n"
        "Если возникли проблемы, звоните: +998 50 747 49 34\n\n"
        "<i>Версия бота: 1.0.0 (Beta)</i>",
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("club:"))
async def show_club_detail(callback: CallbackQuery):
    """Show details of a specific club."""
    club_id = int(callback.data.split(":")[1])
    
    async with async_session_factory() as session:
        club = await session.get(Club, club_id)
        if not club:
            await callback.answer("Клуб не найден.", show_alert=True)
            return
        
        text = f"""
🏢 <b>{club.name}</b>

📍 Город: {club.city}
📌 Адрес: {club.address}
🔧 Система: {club.driver_type}

Выберите действие:
"""
        await callback.message.edit_text(
            text,
            reply_markup=get_club_detail_keyboard(club.id),
            parse_mode="HTML"
        )

@router.callback_query(F.data.startswith("location:"))
async def send_club_location(callback: CallbackQuery):
    """Send club location map."""
    club_id = int(callback.data.split(":")[1])
    
    async with async_session_factory() as session:
        club = await session.get(Club, club_id)
        if not club:
            await callback.answer("Клуб не найден.", show_alert=True)
            return
            
        # Try to parse coordinates from address or use default for Tashkent
        # Ideally, Club model should have lat/lon fields.
        # For now, we'll use a placeholder or try to geocode if we had a service.
        # Let's use a fixed location for Arenaslot as an example or generic Tashkent center
        
        # Use club's actual GPS coordinates if set, fallback to Tashkent center
        latitude = club.latitude if club.latitude else 41.2995
        longitude = club.longitude if club.longitude else 69.2401
        
        await callback.message.answer_location(
            latitude=latitude,
            longitude=longitude
        )
        await callback.answer()

@router.callback_query(F.data.startswith("view_pcs:"))
async def show_zones(callback: CallbackQuery):
    """Show zones for a club instead of all PCs."""
    club_id = int(callback.data.split(":")[1])
    
    async with async_session_factory() as session:
        club = await session.get(Club, club_id)
        if not club:
            await callback.answer("Клуб не найден.", show_alert=True)
            return
        
        # Load driver and fetch zones
        driver = DriverFactory.get_driver(club.driver_type, {"club_id": club.id, **club.connection_config})
        zones = await driver.get_club_zones()
        
        if not zones:
            await callback.answer("Нет информации о зонах.", show_alert=True)
            return
            
        from keyboards.zones import get_zones_keyboard
        
        await callback.message.edit_text(
            f"🏢 <b>Зоны в клубе {club.name}</b>\n\n"
            "Выберите зону, чтобы посмотреть свободные компьютеры:",
            reply_markup=get_zones_keyboard(club.id, zones),
            parse_mode="HTML"
        )

@router.callback_query(F.data.startswith("view_zone_pcs:"))
async def show_zone_computers(callback: CallbackQuery):
    """Show computers for a specific zone."""
    parts = callback.data.split(":")
    club_id = int(parts[1])
    zone_name = parts[2]
    
    async with async_session_factory() as session:
        club = await session.get(Club, club_id)
        
        driver = DriverFactory.get_driver(club.driver_type, {"club_id": club.id, **club.connection_config})
        computers = await driver.get_computers()
        
        # Filter by zone
        zone_computers = [pc for pc in computers if pc.zone == zone_name]
        
        if not zone_computers:
            await callback.answer("В этой зоне нет компьютеров.", show_alert=True)
            return
            
        # Use existing PC keyboard but with filtered list
        # Pass a "back to zones" callback if possible, but get_computers_keyboard has hardcoded back button
        # We might need to update get_computers_keyboard to accept custom back callback or handle it
        
        # For now, let's just show them. The back button in get_computers_keyboard goes to "club:{club_id}"
        # Ideally it should go back to "view_pcs:{club_id}" (which now shows zones)
        
        text = f"💻 <b>Компьютеры в зоне {zone_name}</b>\n\nВыберите ПК для бронирования:"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_computers_keyboard(club.id, zone_computers),
            parse_mode="HTML"
        )

@router.callback_query(F.data.startswith("book:"))
async def show_date_selection(callback: CallbackQuery):
    """Show date selection for booking."""
    parts = callback.data.split(":")
    club_id = int(parts[1])
    pc_id = parts[2]
    
    async with async_session_factory() as session:
        club = await session.get(Club, club_id)
        
        await callback.message.edit_text(
            f"📅 <b>Выберите дату бронирования</b>\n\n"
            f"Компьютер: PC-{pc_id}\n"
            f"Клуб: {club.name}",
            reply_markup=get_date_keyboard(club_id, pc_id),
            parse_mode="HTML"
        )

@router.callback_query(F.data.startswith("date:"))
async def show_time_selection(callback: CallbackQuery):
    """Show time selection for booking."""
    parts = callback.data.split(":")
    club_id = int(parts[1])
    pc_id = parts[2]
    day_offset = int(parts[3])
    
    from datetime import datetime, timedelta
    from utils.timezone import now_tashkent
    selected_date = now_tashkent() + timedelta(days=day_offset)
    date_str = "Сегодня" if day_offset == 0 else "Завтра"
    
    async with async_session_factory() as session:
        club = await session.get(Club, club_id)
        
        # Get time keyboard with availability info
        time_kb = await get_time_keyboard(club_id, pc_id, day_offset)
        
        await callback.message.edit_text(
            f"🕐 <b>Выберите время начала</b>\n\n"
            f"Компьютер: PC-{pc_id}\n"
            f"Клуб: {club.name}\n"
            f"Дата: {date_str} ({selected_date.strftime('%d.%m')})\n\n"
            f"✅ - Свободно\n"
            f"❌ - Занято (но можно попробовать)",
            reply_markup=time_kb,
            parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("time:"))
async def show_duration_selection_direct(callback: CallbackQuery):
    """Show duration selection directly after time selection."""
    parts = callback.data.split(":")
    club_id = int(parts[1])
    pc_id = parts[2]
    day_offset = int(parts[3])
    hour = int(parts[4])
    
    # Minute is always 0 (on the hour)
    minute = 0
    
    from datetime import datetime, timedelta
    from utils.timezone import now_tashkent
    selected_date = now_tashkent() + timedelta(days=day_offset)
    date_str = "Сегодня" if day_offset == 0 else "Завтра"
    
    async with async_session_factory() as session:
        club = await session.get(Club, club_id)
        
        await callback.message.edit_text(
            f"⏱ <b>Выберите длительность</b>\n\n"
            f"Компьютер: PC-{pc_id}\n"
            f"Клуб: {club.name}\n"
            f"Дата: {date_str} ({selected_date.strftime('%d.%m')})\n"
            f"Время начала: {hour:02d}:00",
            reply_markup=get_duration_keyboard(club_id, pc_id, day_offset, hour, minute),
            parse_mode="HTML"
        )



@router.callback_query(F.data.startswith("minute:"))
async def show_duration_selection(callback: CallbackQuery):
    """Show duration selection."""
    parts = callback.data.split(":")
    club_id = int(parts[1])
    pc_id = parts[2]
    day_offset = int(parts[3])
    hour = int(parts[4])
    minute = int(parts[5])
    
    from datetime import datetime, timedelta
    from utils.timezone import now_tashkent
    selected_date = now_tashkent() + timedelta(days=day_offset)
    date_str = "Сегодня" if day_offset == 0 else "Завтра"
    
    async with async_session_factory() as session:
        club = await session.get(Club, club_id)
        
        await callback.message.edit_text(
            f"⏱ <b>Выберите длительность</b>\n\n"
            f"Компьютер: PC-{pc_id}\n"
            f"Клуб: {club.name}\n"
            f"Дата: {date_str} ({selected_date.strftime('%d.%m')})\n"
            f"Время начала: {hour:02d}:{minute:02d}",
            reply_markup=get_duration_keyboard(club_id, pc_id, day_offset, hour, minute),
            parse_mode="HTML"
        )

@router.callback_query(F.data.startswith("duration:"))
async def book_with_duration(callback: CallbackQuery):
    """Book computer with selected time and duration."""
    parts = callback.data.split(":")
    club_id = int(parts[1])
    pc_id = parts[2]
    day_offset = int(parts[3])
    start_hour = int(parts[4])
    start_minute = int(parts[5])
    duration_minutes = int(parts[6])
    
    async with async_session_factory() as session:
        club = await session.get(Club, club_id)
        
        # Get or create current user
        result = await session.execute(
            select(User).where(User.tg_id == callback.from_user.id)
        )
        user = result.scalars().first()
        
        if not user:
            # Auto-register user
            user = User(
                tg_id=callback.from_user.id,
                username=callback.from_user.username,
                full_name=callback.from_user.full_name
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        
        # Calculate start time with minutes
        from datetime import datetime, timedelta
        from utils.timezone import now_tashkent
        now = now_tashkent()
        start_time = now.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0) + timedelta(days=day_offset)
        
        # Book with selected parameters
        driver = DriverFactory.get_driver(club.driver_type, {"club_id": club.id, **club.connection_config})
        result = await driver.reserve_pc(pc_id, user.id, start_time, duration_minutes)
        
        if result.success:
            date_str = "Сегодня" if day_offset == 0 else "Завтра"
            end_time = start_time + timedelta(minutes=duration_minutes)
            await callback.answer(
                f"✅ Забронировано!\n{date_str} {start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')}", 
                show_alert=True
            )
            
            # Auto-refresh the computer list
            computers = await driver.get_computers()
            text = f"💻 <b>Компьютеры в {club.name}</b>\n\nВыберите ПК для бронирования:"
            await callback.message.edit_text(
                text,
                reply_markup=get_computers_keyboard(club.id, computers),
                parse_mode="HTML"
            )
        else:
            # Show detailed conflict information
            if result.conflict_info:
                from datetime import timedelta
                conflict_start = result.conflict_info['start_dt']
                conflict_end = result.conflict_info['end_dt']
                
                msg = (
                    f"❌ <b>Компьютер уже забронирован!</b>\n\n"
                    f"Занято: {result.conflict_info['start']} - {result.conflict_info['end']}\n\n"
                    f"<b>Вы можете забронировать:</b>\n"
                )
                
                # Suggest booking before conflict
                if start_time < conflict_start:
                    time_before = int((conflict_start - start_time).total_seconds() / 60)
                    if time_before >= 30:
                        msg += f"• До {result.conflict_info['start']} (максимум {time_before} мин)\n"
                
                # Suggest booking after conflict
                msg += f"• После {result.conflict_info['end']}"
                
                await callback.answer(msg, show_alert=True, parse_mode="HTML")
            else:
                await callback.answer(f"❌ {result.message}", show_alert=True)


@router.callback_query(F.data.startswith("cancel_booking:"))
async def cancel_booking(callback: CallbackQuery):
    """Cancel a booking."""
    booking_id = int(callback.data.split(":")[1])
    
    async with async_session_factory() as session:
        async with session.begin():
            booking = await session.get(Booking, booking_id)
            
            if not booking:
                await callback.answer("Бронь не найдена.", show_alert=True)
                return
            
            # Check if this booking belongs to the user
            result = await session.execute(
                select(User).where(User.tg_id == callback.from_user.id)
            )
            user = result.scalars().first()
            
            if not user or booking.user_id != user.id:
                await callback.answer("Это не ваша бронь!", show_alert=True)
                return
            
            if booking.status != "CONFIRMED":
                await callback.answer("Эта бронь уже отменена или завершена.", show_alert=True)
                return
            
            # Cancel the booking
            booking.status = "CANCELLED"
            await session.commit()
        
        await callback.answer("✅ Бронь успешно отменена!", show_alert=True)
        
        # Refresh the bookings list
        # ✅ FIX: Use eager loading to avoid N+1 query
        from sqlalchemy.orm import selectinload
        
        result = await session.execute(
            select(Booking)
            .options(selectinload(Booking.club))
            .where(Booking.user_id == user.id)
            .order_by(Booking.start_time.desc())
        )
        bookings = result.scalars().all()
        
        if not bookings:
            text = "📋 <b>Мои брони</b>\n\nУ вас пока нет бронирований."
            keyboard = get_main_menu()
        else:
            text = "📋 <b>Мои брони</b>\n\n"
            buttons = []
            
            for b in bookings:
                club = b.club  # ✅ Already loaded
                
                if b.status == "CONFIRMED":
                    status_emoji = "🟡"
                    status_text = "Ожидает"
                elif b.status == "ACTIVE":
                    status_emoji = "🟢"
                    status_text = "Играет"
                elif b.status == "COMPLETED":
                    status_emoji = "✅"
                    status_text = "Завершено"
                elif b.status == "NO_SHOW":
                    status_emoji = "❌"
                    status_text = "Не пришел"
                elif b.status == "CANCELLED":
                    status_emoji = "❌"
                    status_text = "Отменено"
                else:
                    status_emoji = "⏳"
                    status_text = b.status
                
                from datetime import timezone, timedelta
                tz = timezone(timedelta(hours=5))
                text += f"{status_emoji} <b>{b.computer_name}</b> в {club.name}\n"
                text += f"  {b.start_time.astimezone(tz).strftime('%d.%m %H:%M')} - {b.end_time.astimezone(tz).strftime('%H:%M')}\n"
                text += f"  Статус: {status_text}\n\n"
                
                if b.status == "CONFIRMED":
                    from aiogram.types import InlineKeyboardButton
                    buttons.append([
                        InlineKeyboardButton(
                            text=f"❌ Отменить {b.computer_name} ({b.start_time.astimezone(tz).strftime('%d.%m %H:%M')})",
                            callback_data=f"cancel_booking:{b.id}"
                        )
                    ])
            
            # Add clear history button
            has_old_bookings = any(b.status in ["COMPLETED", "CANCELLED", "NO_SHOW"] for b in bookings)
            if has_old_bookings:
                from aiogram.types import InlineKeyboardButton
                buttons.append([InlineKeyboardButton(text="🗑 Очистить историю", callback_data="clear_history")])
            
            from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
            buttons.append([InlineKeyboardButton(text="« Назад", callback_data="back_main")])
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback.message.edit_text(
            text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )

@router.callback_query(F.data == "clear_history")
async def clear_history(callback: CallbackQuery):
    """Clear completed and cancelled bookings history."""
    async with async_session_factory() as session:
        # Get user
        result = await session.execute(
            select(User).where(User.tg_id == callback.from_user.id)
        )
        user = result.scalars().first()
        
        if not user:
            await callback.answer("Вы не зарегистрированы.", show_alert=True)
            return
        
        # Delete old bookings
        result = await session.execute(
            select(Booking).where(
                and_(
                    Booking.user_id == user.id,
                    Booking.status.in_(["COMPLETED", "CANCELLED", "NO_SHOW"])
                )
            )
        )
        old_bookings = result.scalars().all()
        count = len(old_bookings)
        
        for booking in old_bookings:
            await session.delete(booking)
        
        await session.commit()
        
        await callback.answer(f"✅ Удалено записей: {count}", show_alert=True)
        
        # Refresh bookings list
        # ✅ FIX: Use eager loading to avoid N+1 query
        from sqlalchemy.orm import selectinload
        
        result = await session.execute(
            select(Booking)
            .options(selectinload(Booking.club))
            .where(Booking.user_id == user.id)
            .order_by(Booking.start_time.desc())
        )
        bookings = result.scalars().all()
        
        if not bookings:
            text = "📋 <b>Мои брони</b>\n\nУ вас пока нет бронирований."
            keyboard = get_main_menu()
        else:
            text = "📋 <b>Мои брони</b>\n\n"
            buttons = []
            
            for b in bookings:
                club = b.club  # ✅ Already loaded
                
                if b.status == "CONFIRMED":
                    status_emoji = "🟡"
                    status_text = "Ожидает"
                elif b.status == "ACTIVE":
                    status_emoji = "🟢"
                    status_text = "Играет"
                elif b.status == "COMPLETED":
                    status_emoji = "✅"
                    status_text = "Завершено"
                elif b.status == "NO_SHOW":
                    status_emoji = "❌"
                    status_text = "Не пришел"
                elif b.status == "CANCELLED":
                    status_emoji = "❌"
                    status_text = "Отменено"
                else:
                    status_emoji = "⏳"
                    status_text = b.status
                
                from datetime import timezone, timedelta
                tz = timezone(timedelta(hours=5))
                text += f"{status_emoji} <b>{b.computer_name}</b> в {club.name}\n"
                text += f"  {b.start_time.astimezone(tz).strftime('%d.%m %H:%M')} - {b.end_time.astimezone(tz).strftime('%H:%M')}\n"
                text += f"  Статус: {status_text}\n\n"
                
                if b.status == "CONFIRMED":
                    from aiogram.types import InlineKeyboardButton
                    buttons.append([
                        InlineKeyboardButton(
                            text=f"❌ Отменить {b.computer_name} ({b.start_time.astimezone(tz).strftime('%d.%m %H:%M')})",
                            callback_data=f"cancel_booking:{b.id}"
                        )
                    ])
            
            from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
            buttons.append([InlineKeyboardButton(text="« Назад", callback_data="back_main")])
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback.message.edit_text(
            text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
