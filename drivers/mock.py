from datetime import datetime, timedelta
from utils.timezone import now_tashkent
from typing import List, Optional
import asyncio
from sqlalchemy import select, and_, or_

from .base import BaseDriver, ComputerSchema, ZoneSchema, BookingResult
from database import async_session_factory
from models import Booking, User, Club, Computer
import random
import string

class MockDriver(BaseDriver):
    """
    Driver using database records to simulate a real club.
    Used for Investor Demos.
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.club_id = config.get("club_id")
    
    async def get_computers(self) -> List[ComputerSchema]:
        # Simulate network delay
        await asyncio.sleep(0.1)
        
        async with async_session_factory() as session:
            # Check for conflicting bookings
            now = now_tashkent()
            result = await session.execute(
                select(Booking).where(
                    and_(
                        Booking.club_id == self.club_id,
                        Booking.status == "CONFIRMED",
                        Booking.start_time <= now,
                        Booking.end_time >= now
                    )
                )
            )
            active_bookings = result.scalars().all()
            booked_pc_names = {b.computer_name for b in active_bookings}
            
            # Fetch computers from DB
            from models import Computer
            result = await session.execute(
                select(Computer).where(
                    and_(
                        Computer.club_id == self.club_id,
                        Computer.is_active == True
                    )
                )
            )
            db_computers = result.scalars().all()
            
            computers = []
            for pc in db_computers:
                computers.append(ComputerSchema(
                    id=str(pc.id),
                    name=pc.name,
                    zone=pc.zone,
                    is_available=pc.name not in booked_pc_names,
                    price_per_hour=pc.price_per_hour,
                    cpu=pc.cpu,
                    gpu=pc.gpu,
                    ram_gb=pc.ram_gb,
                    monitor_hz=pc.monitor_hz
                ))
            
            return computers

    async def get_club_zones(self) -> List[ZoneSchema]:
        """Dynamically build zones from database computers."""
        computers = await self.get_computers()
        
        # Group by zones
        zones_dict = {}
        for pc in computers:
            if pc.zone not in zones_dict:
                zones_dict[pc.zone] = {
                    "total": 0,
                    "available": 0,
                    "min_price": float('inf'),
                    "cpu": pc.cpu,
                    "gpu": pc.gpu,
                    "ram_gb": pc.ram_gb,
                    "monitor_hz": pc.monitor_hz
                }
            
            zones_dict[pc.zone]["total"] += 1
            if pc.is_available:
                zones_dict[pc.zone]["available"] += 1
            
            if pc.price_per_hour < zones_dict[pc.zone]["min_price"]:
                zones_dict[pc.zone]["min_price"] = pc.price_per_hour
        
        zones = []
        for zone_name, data in zones_dict.items():
            zones.append(ZoneSchema(
                name=zone_name,
                min_price=data["min_price"] if data["min_price"] != float('inf') else 0,
                total_pcs=data["total"],
                available_pcs=data["available"],
                cpu=data.get("cpu"),
                gpu=data.get("gpu"),
                ram_gb=data.get("ram_gb"),
                monitor_hz=data.get("monitor_hz")
            ))
        
        return zones

    async def check_availability(self, pc_id: str, start_time: datetime, duration_minutes: int) -> bool:
        """Check availability using DB records."""
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        async with async_session_factory() as session:
            # First get the computer to check if it exists and get its name
            from models import Computer
            pc = await session.get(Computer, int(pc_id))
            if not pc:
                return False
                
            pc_name = pc.name
            
            # Check for overlapping bookings
            result = await session.execute(
                select(Booking).where(
                    and_(
                        Booking.club_id == self.club_id,
                        Booking.computer_name == pc_name,
                        Booking.status == "CONFIRMED",
                        Booking.start_time < end_time,
                        Booking.end_time > start_time
                    )
                )
            )
            overlapping = result.scalars().first()
            return overlapping is None

    async def reserve_pc(self, pc_id: str, user_id: int, start_time: datetime, duration_minutes: int) -> BookingResult:
        """Reserve PC using DB records."""
        # Simulate network delay for mock
        await asyncio.sleep(0.5)
        
        async with async_session_factory() as session:
            async with session.begin():
                try:
                    # Get computer details first
                    from models import Computer
                    pc = await session.get(Computer, int(pc_id))
                    if not pc:
                        return BookingResult(success=False, message="Компьютер не найден")
                        
                    pc_name = pc.name
                    end_time = start_time + timedelta(minutes=duration_minutes)
                    
                    # Check for conflicts
                    result = await session.execute(
                        select(Booking).where(
                            and_(
                                Booking.club_id == self.club_id,
                                Booking.computer_name == pc_name,
                                Booking.status == "CONFIRMED",
                                Booking.start_time < end_time,
                                Booking.end_time > start_time
                            )
                        )
                    )
                    conflict = result.scalars().first()
                    if conflict:
                        return BookingResult(
                            success=False, 
                            message="Уже забронировано другим пользователем!",
                            conflict_info={
                                "start": conflict.start_time.strftime("%d.%m %H:%M"),
                                "end": conflict.end_time.strftime("%H:%M"),
                                "start_dt": conflict.start_time,
                                "end_dt": conflict.end_time
                            }
                        )
                    
                    # Use the provided user_id
                    user = await session.get(User, user_id)
                    if not user:
                        return BookingResult(success=False, message="Пользователь не найден")
                    
                    # Generate 6-char confirmation code
                    conf_code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
                    
                    # Create booking
                    booking = Booking(
                        user_id=user.id,
                        club_id=self.club_id,
                        computer_name=pc_name,
                        item_id=int(pc_id),
                        start_time=start_time,
                        end_time=end_time,
                        status="CONFIRMED",
                        confirmation_code=conf_code
                    )
                    session.add(booking)
                    await session.flush()
                    
                    return BookingResult(
                        success=True,
                        message=f"Забронировано {pc_name} на {duration_minutes} минут",
                        booking_id=str(booking.id)
                    )
                except Exception as e:
                    return BookingResult(success=False, message=f"Ошибка: {str(e)}")
