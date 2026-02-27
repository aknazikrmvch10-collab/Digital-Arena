"""
Review handler: processes star ratings submitted after a booking via inline buttons.
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy import select
from database import async_session_factory
from models import User, Review, Booking, Club

router = Router()


@router.callback_query(F.data.startswith("review:"))
async def handle_review(callback: CallbackQuery):
    """Handle review button press: review:{booking_id}:{rating}"""
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Неверный формат", show_alert=True)
        return

    booking_id = int(parts[1])
    rating = int(parts[2])

    if rating < 1 or rating > 5:
        await callback.answer("Некорректная оценка", show_alert=True)
        return

    stars = "⭐" * rating

    async with async_session_factory() as session:
        async with session.begin():
            # Check if review already exists
            existing = await session.execute(
                select(Review).where(Review.booking_id == booking_id)
            )
            if existing.scalars().first():
                await callback.answer("Вы уже оставили отзыв на эту бронь!", show_alert=True)
                return

            # Check booking ownership
            booking = await session.get(Booking, booking_id)
            if not booking:
                await callback.answer("Бронь не найдена", show_alert=True)
                return

            user_result = await session.execute(
                select(User).where(User.tg_id == callback.from_user.id)
            )
            user = user_result.scalars().first()
            if not user or booking.user_id != user.id:
                await callback.answer("Это не ваша бронь", show_alert=True)
                return

            # Save review
            review = Review(
                user_id=user.id,
                club_id=booking.club_id,
                booking_id=booking_id,
                rating=rating
            )
            session.add(review)

    club = None
    async with async_session_factory() as session:
        club = await session.get(Club, booking.club_id)

    club_name = club.name if club else "клуб"
    await callback.message.edit_text(
        f"✅ <b>Спасибо за отзыв!</b>\n\n"
        f"Вы оценили <b>{club_name}</b> на {stars} ({rating}/5)\n\n"
        f"<i>Ваша оценка поможет другим игрокам выбрать лучший клуб!</i>",
        parse_mode="HTML"
    )
    await callback.answer()
