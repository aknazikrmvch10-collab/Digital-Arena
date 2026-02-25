from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from sqlalchemy import select, and_
from models import User, Booking, Club
from database import async_session_factory
from utils.timezone import now_tashkent

router = Router()

# Note: "👤 Мои брони" and "my_bookings" callback are handled in clubs.py
# This file handles /profile and /phone commands


@router.message(Command("phone"))
async def share_phone_command(message: Message):
    """Allow user to share or update their phone number."""
    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.tg_id == message.from_user.id))
        user = result.scalars().first()

    phone_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Отправить номер", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    if user and user.phone:
        text = (
            f"📱 <b>Ваш текущий номер:</b> {user.phone}\n\n"
            "Хотите обновить? Нажмите кнопку ниже 👇"
        )
    else:
        text = (
            "📱 <b>Укажите ваш номер телефона</b>\n\n"
            "Он нужен для входа на сайте и подтверждения бронирований.\n\n"
            "Нажмите кнопку ниже 👇"
        )

    await message.answer(text, reply_markup=phone_keyboard, parse_mode="HTML")


@router.message(F.text == "⏩ Пропустить")
async def skip_phone_sharing(message: Message):
    """Skip phone sharing and show main menu."""
    from keyboards.main import get_main_reply_keyboard
    await message.answer(
        "👌 Вы можете указать номер позже через /phone\n\n"
        "А пока — пользуйтесь ботом!",
        reply_markup=get_main_reply_keyboard(),
        parse_mode="HTML"
    )

@router.message(Command("profile"))
async def show_profile(event: Message):
    """Show user profile info with active bookings."""
    user_id = event.from_user.id

    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.tg_id == user_id))
        user = result.scalars().first()
        
        if not user:
            await event.answer("❌ Вы не зарегистрированы. Нажмите /start")
            return

        # Get active bookings
        now = now_tashkent()
        bookings_result = await session.execute(
            select(Booking, Club).join(Club, Booking.club_id == Club.id).where(
                and_(
                    Booking.user_id == user.id,
                    Booking.status.in_(["CONFIRMED", "ACTIVE"]),
                    Booking.end_time > now
                )
            ).order_by(Booking.start_time.asc())
        )
        bookings = bookings_result.all()

        text = f"👤 <b>Профиль:</b> {user.full_name}\n"
        text += f"🆔 ID: <code>{user.tg_id}</code>\n"
        phone = user.phone if user.phone else "Не указан"
        text += f"📱 Телефон: {phone}\n\n"
        
        if not bookings:
            text += "📭 <b>У вас нет активных бронирований.</b>\n\n"
            text += "Чтобы забронировать место, нажмите кнопку «🏢 Клубы» или откройте Mini App!"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔍 Найти клубы", callback_data="find_clubs")]
            ])
        else:
            text += "📅 <b>Ваши активные брони:</b>\n\n"
            keyboard_buttons = []
            
            from datetime import timezone, timedelta
            tz = timezone(timedelta(hours=5))
            for booking, club in bookings:
                start = booking.start_time.astimezone(tz).strftime("%d.%m %H:%M")
                end = booking.end_time.astimezone(tz).strftime("%H:%M")
                text += (
                    f"🕹 <b>{club.name}</b>\n"
                    f"🖥 {booking.computer_name}\n"
                    f"🕒 {start} - {end}\n"
                    f"🔑 Код брони: <code>#{booking.id}</code>\n\n"
                )
                keyboard_buttons.append([
                    InlineKeyboardButton(
                        text=f"❌ Отменить #{booking.id}",
                        callback_data=f"cancel_booking:{booking.id}"
                    )
                ])
                
            keyboard_buttons.append([InlineKeyboardButton(text="🔄 Обновить", callback_data="my_bookings")])
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        await event.answer(text, reply_markup=keyboard, parse_mode="HTML")

