from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

class ComputerSchema(BaseModel):
    id: str
    name: str
    zone: str
    is_available: bool
    price_per_hour: float
    # Optional specs for display
    cpu: Optional[str] = None
    gpu: Optional[str] = None
    ram_gb: Optional[int] = None
    monitor_hz: Optional[int] = None

class BookingResult(BaseModel):
    success: bool
    message: str
    booking_id: Optional[str] = None
    conflict_info: Optional[dict] = None  # Info about conflicting booking

class ZoneSchema(BaseModel):
    name: str
    min_price: float
    total_pcs: int
    available_pcs: int
    # Representative specs
    cpu: Optional[str] = None
    gpu: Optional[str] = None
    ram_gb: Optional[int] = None
    monitor_hz: Optional[int] = None
    # Rich UI extensions
    image_url: Optional[str] = None
    description: Optional[str] = None

class BaseDriver(ABC):
    """
    Universal Interface that all Club Drivers must implement.
    """
    
    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    async def get_computers(self) -> List[ComputerSchema]:
        """Returns a list of all computers and their current status."""
        pass

    @abstractmethod
    async def get_club_zones(self) -> List[ZoneSchema]:
        """Returns a list of zones with summary info."""
        pass

    @abstractmethod
    async def check_availability(self, pc_id: str, start_time: datetime, duration_minutes: int) -> bool:
        """Checks if a specific PC is free for the given time slot."""
        pass

    @abstractmethod
    async def reserve_pc(self, pc_id: str, user_id: int, start_time: datetime, duration_minutes: int) -> BookingResult:
        """Attempts to book a PC in the external system."""
        pass
