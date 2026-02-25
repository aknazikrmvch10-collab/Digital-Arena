import asyncio
from datetime import datetime, timedelta
from utils.timezone import now_tashkent
from sqlalchemy import select, and_
from database import async_session_factory
from models import Booking, User, Club
from utils.logging import get_logger

logger = get_logger(__name__)

async def check_no_show_bookings():
    """Check for bookings where client didn't show up within 15 minutes and mark as NO_SHOW."""
    while True:
        try:
            async with async_session_factory() as session:
                async with session.begin():
                    now = now_tashkent()
                    no_show_time = now - timedelta(minutes=15)
                    
                    # Find bookings that started > 15 mins ago, still CONFIRMED, not checked
                    result = await session.execute(
                        select(Booking).where(
                            and_(
                                Booking.status == "CONFIRMED",
                                Booking.start_time <= no_show_time,
                                Booking.check_timeout == False
                            )
                        )
                    )
                    bookings = result.scalars().all()
                    
                    for booking in bookings:
                        booking.status = "NO_SHOW"
                        booking.check_timeout = True
                        logger.info("Auto-cancelled no-show booking", booking_id=booking.id)
                    
                    if bookings:
                        await session.commit()
        except Exception as e:
            logger.error("Error in no-show checker", error=str(e))
        
        # Check every minute
        await asyncio.sleep(60)

async def check_auto_complete_bookings():
    """Automatically mark bookings as COMPLETED when end_time passes."""
    while True:
        try:
            async with async_session_factory() as session:
                async with session.begin():
                    now = now_tashkent()
                    
                    # Find ACTIVE bookings that have ended
                    result = await session.execute(
                        select(Booking).where(
                            and_(
                                Booking.status == "ACTIVE",
                                Booking.end_time <= now
                            )
                        )
                    )
                    bookings = result.scalars().all()
                    
                    for booking in bookings:
                        booking.status = "COMPLETED"
                        logger.info("Auto-completed booking", booking_id=booking.id)
                    
                    if bookings:
                        await session.commit()
        except Exception as e:
            logger.error("Error in auto-complete checker", error=str(e))
        
        # Check every minute
        await asyncio.sleep(60)

async def send_reminder_notifications(bot):
    """Send reminder notifications to clients based on their preferences."""
    while True:
        try:
            async with async_session_factory() as session:
                from datetime import datetime, timedelta
                now = now_tashkent()
                
                # Check for each possible notification time (15, 30, 60 minutes)
                for minutes in [15, 30, 60]:
                    # Find bookings starting in ~X minutes (X-2 to X+2 min window)
                    time_lower = now + timedelta(minutes=minutes-2)
                    time_upper = now + timedelta(minutes=minutes+2)
                    
                    result = await session.execute(
                        select(Booking).where(
                            and_(
                                Booking.status == "CONFIRMED",
                                Booking.notification_sent == False,
                                Booking.start_time >= time_lower,
                                Booking.start_time <= time_upper
                            )
                        )
                    )
                    bookings = result.scalars().all()
                    
                    for booking in bookings:
                        try:
                            # Get user and check their preferences
                            user = await session.get(User, booking.user_id)
                            
                            if not user:
                                continue
                            
                            # Skip if notifications disabled
                            if not user.notifications_enabled:
                                continue
                            
                            # Only send if user's preference matches this timing
                            if user.notification_minutes != minutes:
                                continue
                            
                            # Get club info
                            club = await session.get(Club, booking.club_id)
                            
                            if user and club:
                                # Calculate exact time until booking
                                time_until = int((booking.start_time - now).total_seconds() / 60)
                                
                                message = (
                                    f"⏰ <b>Напоминание!</b>\n\n"
                                    f"Ваша бронь через {time_until} минут:\n"
                                    f"💻 {booking.computer_name} в {club.name}\n"
                                    f"🕐 Время: {booking.start_time.strftime('%H:%M')}-{booking.end_time.strftime('%H:%M')}\n"
                                    f"📍 Адрес: {club.address}\n\n"
                                    f"Не опоздайте! 🏃"
                                )
                                
                                # Send notification
                                await bot.send_message(
                                    chat_id=user.tg_id,
                                    text=message,
                                    parse_mode="HTML"
                                )
                                
                                # Mark as sent
                                booking.notification_sent = True
                                logger.info("Sent reminder notification",
                                            minutes=minutes,
                                            booking_id=booking.id,
                                            user_tg_id=user.tg_id)
                        
                        except Exception as e:
                            logger.error("Error sending notification",
                                         booking_id=booking.id, error=str(e))
                    
                    if bookings:
                        await session.commit()
                    
        except Exception as e:
            logger.error("Error in reminder notifications", error=str(e))
        
        # Check every minute
        await asyncio.sleep(60)
