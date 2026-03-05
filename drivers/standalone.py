import logging
from datetime import datetime, timedelta
from typing import List
from utils.timezone import now_tashkent
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseDriver, ComputerSchema, BookingResult, ZoneSchema
from models import Computer, Booking, Club, User
from database import async_session_factory
import random
import string

logger = logging.getLogger(__name__)

class StandaloneDriver(BaseDriver):
    """
    Driver for clubs that use the bot as their primary management system.
    Interacts directly with the local database.
    """
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.club_id = config.get("club_id")
        if not self.club_id:
            raise ValueError("club_id is required in config for StandaloneDriver")

    async def get_computers(self) -> List[ComputerSchema]:
        """
        Get all active computers for this club with their current availability status.
        """
        async with async_session_factory() as session:
            # Get only active computers for this club
            result = await session.execute(
                select(Computer).where(
                    and_(
                        Computer.club_id == self.club_id,
                        Computer.is_active == True
                    )
                )
            )
            computers = result.scalars().all()
            
            if not computers:
                logger.warning(f"No active computers found for club_id={self.club_id}")
                return []
            
            # Check current active bookings (CONFIRMED or ACTIVE status)
            now = now_tashkent()
            result = await session.execute(
                select(Booking).where(
                    and_(
                        Booking.club_id == self.club_id,
                        Booking.status.in_(["CONFIRMED", "ACTIVE"]),
                        Booking.start_time <= now,
                        Booking.end_time >= now
                    )
                )
            )
            active_bookings = result.scalars().all()
            booked_pc_names = {b.computer_name for b in active_bookings}
            
            logger.debug(f"Found {len(computers)} computers, {len(booked_pc_names)} currently booked")
            
            return [
                ComputerSchema(
                    id=str(comp.id),
                    name=comp.name,
                    zone=comp.zone,
                    is_available=comp.name not in booked_pc_names,
                    price_per_hour=float(comp.price_per_hour) if comp.price_per_hour else 15000.0,
                    # Pass specs for display
                    cpu=comp.cpu,
                    gpu=comp.gpu,
                    ram_gb=comp.ram_gb,
                    monitor_hz=comp.monitor_hz
                )
                for comp in computers
            ]

    async def get_club_zones(self) -> List[ZoneSchema]:
        """Aggregate computers into zones."""
        computers = await self.get_computers()
        
        zones = {}
        for pc in computers:
            if pc.zone not in zones:
                zones[pc.zone] = {
                    "name": pc.zone,
                    "min_price": pc.price_per_hour,
                    "total_pcs": 0,
                    "available_pcs": 0,
                    "cpu": pc.cpu,
                    "gpu": pc.gpu,
                    "ram_gb": pc.ram_gb,
                    "monitor_hz": pc.monitor_hz
                }
            
            z = zones[pc.zone]
            z["total_pcs"] += 1
            if pc.is_available:
                z["available_pcs"] += 1
            # Keep lowest price
            if pc.price_per_hour < z["min_price"]:
                z["min_price"] = pc.price_per_hour
                
        return [ZoneSchema(**z) for z in zones.values()]

    async def check_availability(self, pc_id: str, start_time: datetime, duration_minutes: int) -> bool:
        """
        Check if a computer is available for the specified time slot.
        
        Args:
            pc_id: Computer ID
            start_time: Start time of the booking
            duration_minutes: Duration in minutes
            
        Returns:
            True if available, False otherwise
        """
        # Validate inputs
        if duration_minutes <= 0:
            logger.warning(f"Invalid duration_minutes: {duration_minutes}")
            return False
        
        if start_time.tzinfo is not None:
            start_time = start_time

        if start_time < now_tashkent():
            logger.warning(f"Start time is in the past: {start_time}")
            return False
        
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        async with async_session_factory() as session:
            # Get computer and verify it belongs to this club
            computer = await session.get(Computer, int(pc_id))
            if not computer:
                logger.warning(f"Computer {pc_id} not found")
                return False
            
            if computer.club_id != self.club_id:
                logger.warning(f"Computer {pc_id} does not belong to club {self.club_id}")
                return False
            
            if not computer.is_active:
                logger.warning(f"Computer {pc_id} is not active")
                return False
            
            # Check for overlapping bookings (CONFIRMED or ACTIVE)
            result = await session.execute(
                select(Booking).where(
                    and_(
                        Booking.club_id == self.club_id,
                        Booking.computer_name == computer.name,
                        Booking.status.in_(["CONFIRMED", "ACTIVE"]),
                        Booking.start_time < end_time,
                        Booking.end_time > start_time
                    )
                )
            )
            overlapping = result.scalars().first()
            return overlapping is None

    async def reserve_pc(self, pc_id: str, user_id: int, start_time: datetime, duration_minutes: int) -> BookingResult:
        """
        Reserve a computer for a user.
        
        Args:
            pc_id: Computer ID
            user_id: User database ID (not Telegram ID)
            start_time: Start time of the booking
            duration_minutes: Duration in minutes
            
        Returns:
            BookingResult with success status and details
        """
        # Validate inputs
        if duration_minutes <= 0:
            return BookingResult(success=False, message="Длительность должна быть больше 0 минут")
        
        # Remove timezone info for comparison if present
        if start_time.tzinfo is not None:
             start_time = start_time # Make naive
             
        if start_time < now_tashkent():
            return BookingResult(success=False, message="Нельзя бронировать в прошлом")
        
        async with async_session_factory() as session:
            async with session.begin():  # Transaction!
                try:
                    # Get computer and verify it belongs to this club
                    computer = await session.get(Computer, int(pc_id))
                    if not computer:
                        logger.warning(f"Computer {pc_id} not found")
                        return BookingResult(success=False, message="Компьютер не найден")
                    
                    if computer.club_id != self.club_id:
                        logger.warning(f"Computer {pc_id} does not belong to club {self.club_id}")
                        return BookingResult(success=False, message="Компьютер не принадлежит этому клубу")
                    
                    if not computer.is_active:
                        logger.warning(f"Computer {pc_id} is not active")
                        return BookingResult(success=False, message="Компьютер неактивен")
                    
                    # Final availability check INSIDE transaction
                    end_time = start_time + timedelta(minutes=duration_minutes)
                    result = await session.execute(
                        select(Booking).where(
                            and_(
                                Booking.club_id == self.club_id,
                                Booking.computer_name == computer.name,
                                Booking.status.in_(["CONFIRMED", "ACTIVE"]),
                                Booking.start_time < end_time,
                                Booking.end_time > start_time
                            )
                        )
                    )
                    conflict = result.scalars().first()
                    if conflict:
                        logger.info(f"Booking conflict for PC {pc_id}: existing booking {conflict.id}")
                        from utils.timezone import to_tashkent as _to_tash
                        return BookingResult(
                            success=False, 
                            message="Уже забронировано другим пользователем!",
                            conflict_info={
                                "start": _to_tash(conflict.start_time).strftime("%d.%m %H:%M"),
                                "end": _to_tash(conflict.end_time).strftime("%H:%M"),
                                "start_dt": conflict.start_time,
                                "end_dt": conflict.end_time
                            }
                        )
                    
                    # Get user
                    user = await session.get(User, user_id)
                    if not user:
                        logger.warning(f"User {user_id} not found")
                        return BookingResult(success=False, message="Пользователь не найден")
                    
                    # Generate 6-char confirmation code
                    conf_code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
                    
                    # Create booking
                    booking = Booking(
                        user_id=user.id,
                        club_id=self.club_id,
                        computer_name=computer.name,
                        item_id=int(pc_id),
                        start_time=start_time,
                        end_time=end_time,
                        status="CONFIRMED",
                        confirmation_code=conf_code
                    )
                    session.add(booking)
                    await session.flush()
                    
                    logger.info(f"Successfully booked PC {computer.name} (ID: {pc_id}) for user {user_id} from {start_time} to {end_time}")
                    
                    return BookingResult(
                        success=True,
                        message=f"Забронировано {computer.name} на {duration_minutes} минут",
                        booking_id=str(booking.id)
                    )
                except ValueError as e:
                    logger.error(f"ValueError in reserve_pc: {e}")
                    return BookingResult(success=False, message=f"Ошибка валидации: {str(e)}")
                except Exception as e:
                    logger.error(f"Unexpected error in reserve_pc: {e}", exc_info=True)
                    return BookingResult(success=False, message=f"Ошибка при бронировании: {str(e)}")
