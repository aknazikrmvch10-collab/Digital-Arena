from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select, and_

from models import Club, User, Booking
from database import async_session_factory
from keyboards.main import (get_clubs_keyboard, get_club_detail_keyboard, get_computers_keyboard, 
                              get_main_menu, get_date_keyboard, get_time_keyboard)
from drivers.factory import DriverFactory

router = Router()

@router.callback_query(F.data == "find_clubs")
async def show_clubs_list(callback: CallbackQuery):
    """Show all available clubs."""
    async with async_session_factory() as session:
        result = await session.execute(select(Club).where(Club.is_active == True))
        clubs = result.scalars().all()
        
        if not clubs:
            await callback.answer("Нет доступных клубов.", show_alert=True)
            return
        
        await callback.message.edit_text(
            "🏢 <b>Доступные клубы:</b>\n\nВыберите клуб для просмотра деталей:",
            reply_markup=get_clubs_keyboard(clubs),
            parse_mode="HTML"
        )

@router.callback_query(F.data == "back_main")
async def back_to_main(callback: CallbackQuery):
    """Return to main menu."""
    await callback.message.edit_text(
        f"👋 <b>С возвращением!</b>\n\n"
        "Я — Универсальный бот для бронирования компьютерных клубов Узбекистана.\n"
        "Находите и бронируйте компьютеры в любом клубе через меня!",
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "my_bookings")
async def show_my_bookings(callback: CallbackQuery):
    """Show user's bookings."""
    async with async_session_factory() as session:
        # Get user
        result = await session.execute(
            select(User).where(User.tg_id == callback.from_user.id)
        )
        user = result.scalars().first()
        
        if not user:
            await callback.answer("Вы не зарегистрированы.", show_alert=True)
            return
        
        # Get bookings
        result = await session.execute(
            select(Booking).where(Booking.user_id == user.id).order_by(Booking.start_time.desc())
        )
        bookings = result.scalars().all()
        
        if not bookings:
            text = "📋 <b>Мои брони</b>\n\nУ вас пока нет бронирований."
            keyboard = get_main_menu()
        else:
            text = "📋 <b>Мои брони</b>\n\n"
            buttons = []
            
            for b in bookings:
                # Get club name
                club = await session.get(Club, b.club_id)
                
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
                
                text += f"{status_emoji} <b>{b.computer_name}</b> в {club.name}\n"
                text += f"  {b.start_time.strftime('%d.%m %H:%M')} - {b.end_time.strftime('%H:%M')}\n"
                text += f"  Статус: {status_text}\n\n"
                
                # Add cancel button only for CONFIRMED bookings
                if b.status == "CONFIRMED":
                    from aiogram.types import InlineKeyboardButton
                    buttons.append([
                        InlineKeyboardButton(
                            text=f"❌ Отменить {b.computer_name} ({b.start_time.strftime('%d.%m %H:%M')})",
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
        
        await callback.message.edit_text(
            text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )

@router.callback_query(F.data == "about")
async def show_about(callback: CallbackQuery):
    """Show about info."""
    await callback.message.edit_text(
        "ℹ️ <b>О боте</b>\n\n"
        "Это универсальный бот для бронирования компьютерных клубов Узбекистана.\n\n"
        "Возможности:\n"
        "- Поиск клубов рядом с вами\n"
        "- Просмотр доступности в реальном времени\n"
        "- Мгновенное бронирование компьютеров\n\n"
        "Работает на передовых технологиях!",
        reply_markup=get_main_menu(),
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

@router.callback_query(F.data.startswith("view_pcs:"))
async def show_computers(callback: CallbackQuery):
    """Show all computers for a club via its driver."""
    club_id = int(callback.data.split(":")[1])
    
    async with async_session_factory() as session:
        club = await session.get(Club, club_id)
        if not club:
            await callback.answer("Клуб не найден.", show_alert=True)
            return
        
        # Load the driver and fetch computers
        driver = DriverFactory.get_driver(club.driver_type, {"club_id": club.id, **club.connection_config})
        computers = await driver.get_computers()
        
        if not computers:
            await callback.answer("Нет доступных компьютеров.", show_alert=True)
            return
        
        text = f"💻 <b>Компьютеры в {club.name}</b>\n\nВыберите ПК для бронирования:"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_computers_keyboard(club.id, computers),
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
    selected_date = datetime.now() + timedelta(days=day_offset)
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
async def show_minute_selection(callback: CallbackQuery):
    """Show minute selection for start time."""
    parts = callback.data.split(":")
    club_id = int(parts[1])
    pc_id = parts[2]
    day_offset = int(parts[3])
    hour = int(parts[4])
    
    from datetime import datetime, timedelta
    selected_date = datetime.now() + timedelta(days=day_offset)
    date_str = "Сегодня" if day_offset == 0 else "Завтра"
    
    async with async_session_factory() as session:
        club = await session.get(Club, club_id)
        
        from keyboards.main import get_minute_keyboard
        
        await callback.message.edit_text(
            f"🕐 <b>Выберите минуты</b>\n\n"
            f"Компьютер: PC-{pc_id}\n"
            f"Клуб: {club.name}\n"
            f"Дата: {date_str} ({selected_date.strftime('%d.%m')})\n"
            f"Час: {hour:02d}:__",
            reply_markup=get_minute_keyboard(club_id, pc_id, day_offset, hour),
            parse_mode="HTML"
        )

@router.callback_query(F.data.startswith("minute:"))
async def show_duration_hours(callback: CallbackQuery):
    """Show duration hours selection."""
    parts = callback.data.split(":")
    club_id = int(parts[1])
    pc_id = parts[2]
    day_offset = int(parts[3])
    hour = int(parts[4])
    minute = int(parts[5])
    
    from datetime import datetime, timedelta
    selected_date = datetime.now() + timedelta(days=day_offset)
    date_str = "Сегодня" if day_offset == 0 else "Завтра"
    
    async with async_session_factory() as session:
        club = await session.get(Club, club_id)
        
        from keyboards.main import get_duration_hours_keyboard
        
        await callback.message.edit_text(
            f"⏱ <b>Выберите длительность (часы)</b>\n\n"
            f"Компьютер: PC-{pc_id}\n"
            f"Клуб: {club.name}\n"
            f"Дата: {date_str} ({selected_date.strftime('%d.%m')})\n"
            f"Время начала: {hour:02d}:{minute:02d}",
            reply_markup=get_duration_hours_keyboard(club_id, pc_id, day_offset, hour, minute),
            parse_mode="HTML"
        )

@router.callback_query(F.data.startswith("dur_h:"))
async def show_duration_minutes(callback: CallbackQuery):
    """Show duration minutes selection."""
    parts = callback.data.split(":")
    club_id = int(parts[1])
    pc_id = parts[2]
    day_offset = int(parts[3])
    hour = int(parts[4])
    minute = int(parts[5])
    dur_hours = int(parts[6])
    
    from datetime import datetime, timedelta
    selected_date = datetime.now() + timedelta(days=day_offset)
    date_str = "Сегодня" if day_offset == 0 else "Завтра"
    
    async with async_session_factory() as session:
        club = await session.get(Club, club_id)
        
        from keyboards.main import get_duration_minutes_keyboard
        
        hours_text = "час" if dur_hours == 1 else ("часа" if dur_hours in [2,3,4] else "часов")
        
        await callback.message.edit_text(
            f"⏱ <b>Добавить минуты к длительности</b>\n\n"
            f"Компьютер: PC-{pc_id}\n"
            f"Клуб: {club.name}\n"
            f"Дата: {date_str} ({selected_date.strftime('%d.%m')})\n"
            f"Время начала: {hour:02d}:{minute:02d}\n"
            f"Длительность: {dur_hours} {hours_text} + ?",
            reply_markup=get_duration_minutes_keyboard(club_id, pc_id, day_offset, hour, minute, dur_hours),
            parse_mode="HTML"
        )

@router.callback_query(F.data.startswith("dur_m:"))
async def book_with_precise_time(callback: CallbackQuery):
    """Book computer with precise time and duration."""
    parts = callback.data.split(":")
    club_id = int(parts[1])
    pc_id = parts[2]
    day_offset = int(parts[3])
    start_hour = int(parts[4])
    start_minute = int(parts[5])
    dur_hours = int(parts[6])
    dur_minutes = int(parts[7])
    
    total_duration_minutes = dur_hours * 60 + dur_minutes
    
    # Minimum 15 minutes
    if total_duration_minutes < 15:
        await callback.answer("❌ Минимальная длительность - 15 минут", show_alert=True)
        return
    
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
        now = datetime.now()
        start_time = now.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0) + timedelta(days=day_offset)
        
        # Book with selected parameters
        driver = DriverFactory.get_driver(club.driver_type, {"club_id": club.id, **club.connection_config})
        result = await driver.reserve_pc(pc_id, user.id, start_time, total_duration_minutes)
        
        if result.success:
            date_str = "Сегодня" if day_offset == 0 else "Завтра"
            end_time = start_time + timedelta(minutes=total_duration_minutes)
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
                    if time_before >= 15:
                        msg += f"• До {result.conflict_info['start']} (максимум {time_before} мин)\n"
                
                # Suggest booking after conflict
                msg += f"• После {result.conflict_info['end']}"
                
                await callback.answer(msg, show_alert=True, parse_mode="HTML")
            else:
                await callback.answer(f"❌ {result.message}", show_alert=True)

@router.callback_query(F.data.startswith("duration:"))
async def book_with_duration(callback: CallbackQuery):
    """Book computer with selected date, time and duration."""
    parts = callback.data.split(":")
    club_id = int(parts[1])
    pc_id = parts[2]
    day_offset = int(parts[3])
    hour = int(parts[4])
    duration = int(parts[5])
    
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
        
        # Calculate start time
        from datetime import datetime, timedelta
        now = datetime.now()
        start_time = now.replace(hour=hour, minute=0, second=0, microsecond=0) + timedelta(days=day_offset)
        
        # Book with selected parameters
        driver = DriverFactory.get_driver(club.driver_type, {"club_id": club.id, **club.connection_config})
        result = await driver.reserve_pc(pc_id, user.id, start_time, duration)
        
        if result.success:
            date_str = "Сегодня" if day_offset == 0 else "Завтра"
            await callback.answer(
                f"✅ Забронировано!\n{date_str} в {hour:02d}:00 на {duration} мин", 
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
                suggested_start = conflict_end
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
        result = await session.execute(
            select(Booking).where(Booking.user_id == user.id).order_by(Booking.start_time.desc())
        )
        bookings = result.scalars().all()
        
        if not bookings:
            text = "📋 <b>Мои брони</b>\n\nУ вас пока нет бронирований."
            keyboard = get_main_menu()
        else:
            text = "📋 <b>Мои брони</b>\n\n"
            buttons = []
            
            for b in bookings:
                club = await session.get(Club, b.club_id)
                
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
                
                text += f"{status_emoji} <b>{b.computer_name}</b> в {club.name}\n"
                text += f"  {b.start_time.strftime('%d.%m %H:%M')} - {b.end_time.strftime('%H:%M')}\n"
                text += f"  Статус: {status_text}\n\n"
                
                if b.status == "CONFIRMED":
                    from aiogram.types import InlineKeyboardButton
                    buttons.append([
                        InlineKeyboardButton(
                            text=f"❌ Отменить {b.computer_name} ({b.start_time.strftime('%d.%m %H:%M')})",
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
        result = await session.execute(
            select(Booking).where(Booking.user_id == user.id).order_by(Booking.start_time.desc())
        )
        bookings = result.scalars().all()
        
        if not bookings:
            text = "📋 <b>Мои брони</b>\n\nУ вас пока нет бронирований."
            keyboard = get_main_menu()
        else:
            text = "📋 <b>Мои брони</b>\n\n"
            buttons = []
            
            for b in bookings:
                club = await session.get(Club, b.club_id)
                
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
                
                text += f"{status_emoji} <b>{b.computer_name}</b> в {club.name}\n"
                text += f"  {b.start_time.strftime('%d.%m %H:%M')} - {b.end_time.strftime('%H:%M')}\n"
                text += f"  Статус: {status_text}\n\n"
                
                if b.status == "CONFIRMED":
                    from aiogram.types import InlineKeyboardButton
                    buttons.append([
                        InlineKeyboardButton(
                            text=f"❌ Отменить {b.computer_name} ({b.start_time.strftime('%d.%m %H:%M')})",
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
