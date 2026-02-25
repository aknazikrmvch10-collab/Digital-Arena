"""
iCafe Driver for Club Management System Integration
Based on official API: https://dev.icafecloud.com/docs/
"""
import aiohttp
from datetime import datetime, timedelta
from typing import List, Optional
from .base import BaseDriver, ComputerSchema, ZoneSchema, BookingResult

class ICafeDriver(BaseDriver):
    """
    Driver for iCafe Cloud management system.
    
    Config format:
    {
        "cafe_id": "your_cafe_id",  # Required: Your cafe ID from iCafe Cloud
        "api_token": "your_jwt_token",  # Required: JWT token from API settings
    }
    
    API Documentation: https://dev.icafecloud.com/docs/
    Base URL: https://api.icafecloud.com
    """
    
    BASE_URL = "https://api.icafecloud.com/api/v2"
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.cafe_id = config.get("cafe_id")
        self.api_token = config.get("api_token")
        
        if not self.cafe_id:
            raise ValueError("iCafe driver requires 'cafe_id' in config")
        if not self.api_token:
            raise ValueError("iCafe driver requires 'api_token' in config")
    
    async def _make_request(self, endpoint: str, method: str = "GET", params: dict = None, data: dict = None):
        """Helper method to make HTTP requests to iCafe API."""
        url = f"{self.BASE_URL}/cafe/{self.cafe_id}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                if method == "GET":
                    async with session.get(url, headers=headers, params=params) as response:
                        response.raise_for_status()
                        return await response.json()
                elif method == "POST":
                    async with session.post(url, headers=headers, json=data) as response:
                        response.raise_for_status()
                        return await response.json()
            except aiohttp.ClientError as e:
                raise Exception(f"iCafe API error: {str(e)}")
    
    async def get_computers(self) -> List[ComputerSchema]:
        """
        Get list of all computers from iCafe.
        API: GET /api/v2/cafe/{cafeId}/pcs/action/getPcsList
        """
        try:
            # ✅ FIX: iCafe API requires pc_console_type (0=PC, 1..6=Consoles)
            params = {"pc_console_type": 0}
            response = await self._make_request("pcs/action/getPcsList", params=params)
            
            # iCafe API response format (adjust based on actual response)
            # Assuming response has 'data' field with PC list
            pcs_data = response.get("data", [])
            
            computers = []
            for pc in pcs_data:
                # Map iCafe PC status to availability
                # iCafe statuses: online, offline, busy, etc.
                is_available = pc.get("status") not in ["busy", "offline"]
                
                computers.append(ComputerSchema(
                    id=str(pc.get("id", "")),
                    name=pc.get("pc_name", "Unknown"),
                    zone=pc.get("pc_group_name", "Standard"),  # Use PC group as zone
                    is_available=is_available,
                    price_per_hour=float(pc.get("price", 0)),
                    cpu=None,  # iCafe doesn't provide specs via API
                    gpu=None,
                    ram_gb=None,
                    monitor_hz=None
                ))
            
            return computers
        except Exception as e:
            raise Exception(f"Failed to fetch computers from iCafe: {str(e)}")
    
    async def get_club_zones(self) -> List[ZoneSchema]:
        """
        Get zones summary from iCafe.
        Groups computers by PC groups (zones).
        """
        computers = await self.get_computers()
        
        # Group by zones
        zones_dict = {}
        for pc in computers:
            if pc.zone not in zones_dict:
                zones_dict[pc.zone] = {
                    "total": 0,
                    "available": 0,
                    "min_price": float('inf'),
                }
            
            zones_dict[pc.zone]["total"] += 1
            if pc.is_available:
                zones_dict[pc.zone]["available"] += 1
            
            if pc.price_per_hour < zones_dict[pc.zone]["min_price"]:
                zones_dict[pc.zone]["min_price"] = pc.price_per_hour
        
        zones = []
        for zone_name, zone_data in zones_dict.items():
            zones.append(ZoneSchema(
                name=zone_name,
                min_price=zone_data["min_price"] if zone_data["min_price"] != float('inf') else 0,
                total_pcs=zone_data["total"],
                available_pcs=zone_data["available"],
            ))
        
        return zones
    
    async def check_availability(self, pc_id: str, start_time: datetime, duration_minutes: int) -> bool:
        """
        Check if PC is available for booking.
        """
        # Get current bookings
        try:
            bookings_response = await self._make_request("bookings")
            bookings = bookings_response.get("data", [])
            
            # Check if PC has conflicting booking
            end_time = start_time + timedelta(minutes=duration_minutes)
            
            for booking in bookings:
                if str(booking.get("pc_id")) == pc_id:
                    booking_start = datetime.fromisoformat(booking.get("start_time"))
                    booking_end = datetime.fromisoformat(booking.get("end_time"))
                    
                    # Check for overlap
                    if not (end_time <= booking_start or start_time >= booking_end):
                        return False
            
            # Also check PC current status
            computers = await self.get_computers()
            for pc in computers:
                if pc.id == pc_id:
                    return pc.is_available
            
            return True
        except Exception as e:
            # ✅ FIX #5: If we can't verify availability, assume UNAVAILABLE (fail-safe)
            # Returning True here would cause double-bookings on API failure
            import logging
            logging.getLogger(__name__).error(f"iCafe: can't check availability for pc_id={pc_id}: {e}")
            return False
    
    async def reserve_pc(self, pc_id: str, user_id: int, start_time: datetime, duration_minutes: int) -> BookingResult:
        """
        Reserve a PC in iCafe system.
        API: POST /api/v2/cafe/{cafeId}/bookings
        """
        try:
            # Format booking data for iCafe API
            booking_data = {
                "pc_id": int(pc_id),
                "start_time": start_time.isoformat(),
                "duration": duration_minutes,
                "customer_note": f"Booking from bot - User {user_id}"
            }
            
            response = await self._make_request(
                "bookings",
                method="POST",
                data=booking_data
            )
            
            if response.get("code") == 200 or response.get("success"):
                return BookingResult(
                    success=True,
                    message="Booking created successfully",
                    booking_id=str(response.get("data", {}).get("id", ""))
                )
            else:
                return BookingResult(
                    success=False,
                    message=response.get("message", "Booking failed")
                )
                
        except Exception as e:
            return BookingResult(
                success=False,
                message=f"Error creating booking: {str(e)}"
            )
