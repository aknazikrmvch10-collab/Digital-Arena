"""
Runpad Driver for Club Management System Integration
Based on Runpad API: https://runpad.io/api (documentation)

Runpad — популярное ПО для компьютерных клубов в СНГ.
Этот драйвер реализует интеграцию через REST API Runpad.
"""
import aiohttp
from datetime import datetime, timedelta
from typing import List, Optional
from .base import BaseDriver, ComputerSchema, ZoneSchema, BookingResult


class RunpadDriver(BaseDriver):
    """
    Driver for Runpad management system.
    
    Config format:
    {
        "api_url": "http://localhost:8080",   # Runpad server URL (local or cloud)
        "api_key": "your_api_key",            # API key from Runpad admin panel
        "club_id": "your_club_id"             # Club identifier in Runpad
    }
    """
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.api_url = config.get("api_url", "http://localhost:8080")
        self.api_key = config.get("api_key")
        self.club_id = config.get("club_id")
        
        if not self.api_key:
            raise ValueError("Runpad driver requires 'api_key' in config")
    
    async def _make_request(self, endpoint: str, method: str = "GET", params: dict = None, data: dict = None):
        """Helper method to make HTTP requests to Runpad API."""
        url = f"{self.api_url}/api/v1/{endpoint}"
        headers = {
            "X-API-Key": self.api_key,
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
                raise Exception(f"Runpad API error: {str(e)}")
    
    async def get_computers(self) -> List[ComputerSchema]:
        """
        Get list of all computers from Runpad.
        API: GET /api/v1/computers
        """
        try:
            response = await self._make_request("computers")
            pcs_data = response.get("computers", [])
            
            computers = []
            for pc in pcs_data:
                # Runpad statuses: "free", "busy", "offline", "reserved"
                status = pc.get("status", "offline")
                is_available = status == "free"
                
                computers.append(ComputerSchema(
                    id=str(pc.get("id", "")),
                    name=pc.get("name", "Unknown"),
                    zone=pc.get("group", "Standard"),
                    is_available=is_available,
                    price_per_hour=float(pc.get("tariff", {}).get("price_per_hour", 0)),
                    cpu=pc.get("specs", {}).get("cpu"),
                    gpu=pc.get("specs", {}).get("gpu"),
                    ram_gb=pc.get("specs", {}).get("ram_gb"),
                    monitor_hz=pc.get("specs", {}).get("monitor_hz"),
                ))
            
            return computers
        except Exception as e:
            raise Exception(f"Failed to fetch computers from Runpad: {str(e)}")
    
    async def get_club_zones(self) -> List[ZoneSchema]:
        """
        Get zones summary from Runpad.
        Groups computers by their group field.
        """
        computers = await self.get_computers()
        
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
                    "monitor_hz": pc.monitor_hz,
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
                cpu=zone_data["cpu"],
                gpu=zone_data["gpu"],
                ram_gb=zone_data["ram_gb"],
                monitor_hz=zone_data["monitor_hz"],
            ))
        
        return zones
    
    async def check_availability(self, pc_id: str, start_time: datetime, duration_minutes: int) -> bool:
        """
        Check if PC is available for booking in Runpad.
        API: GET /api/v1/computers/{pc_id}/availability
        """
        try:
            end_time = start_time + timedelta(minutes=duration_minutes)
            params = {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            }
            response = await self._make_request(f"computers/{pc_id}/availability", params=params)
            return response.get("available", False)
        except Exception as e:
            # Log the error if possible, or just ignore and return True for now
            return True  # If can't check, assume available
    
    async def reserve_pc(self, pc_id: str, user_id: int, start_time: datetime, duration_minutes: int) -> BookingResult:
        """
        Reserve a PC in Runpad system.
        API: POST /api/v1/bookings
        """
        try:
            end_time = start_time + timedelta(minutes=duration_minutes)
            booking_data = {
                "computer_id": int(pc_id),
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_minutes": duration_minutes,
                "external_user_id": str(user_id),
                "source": "digital_arena_bot"
            }
            
            response = await self._make_request(
                "bookings",
                method="POST",
                data=booking_data
            )
            
            if response.get("success") or response.get("status") == "created":
                return BookingResult(
                    success=True,
                    message="Бронирование создано успешно",
                    booking_id=str(response.get("booking", {}).get("id", ""))
                )
            else:
                return BookingResult(
                    success=False,
                    message=response.get("error", "Ошибка бронирования")
                )
                
        except Exception as e:
            return BookingResult(
                success=False,
                message=f"Ошибка при создании бронирования в Runpad: {str(e)}"
            )
    
    # === МЕТОДЫ ДЛЯ ФИСКАЛЬНОГО МОНИТОРИНГА ===
    
    async def get_sessions(self, start_date: datetime, end_date: datetime) -> list:
        """
        Get historical PC usage sessions from Runpad.
        API: GET /api/v1/sessions
        Used by Fiscal Monitor to compare usage vs revenue.
        """
        try:
            params = {
                "from": start_date.isoformat(),
                "to": end_date.isoformat()
            }
            response = await self._make_request("sessions", params=params)
            return response.get("sessions", [])
        except Exception as e:
            return []
    
    async def get_revenue_report(self, start_date: datetime, end_date: datetime) -> dict:
        """
        Get revenue report from Runpad.
        API: GET /api/v1/reports/revenue
        """
        try:
            params = {
                "from": start_date.isoformat(),
                "to": end_date.isoformat()
            }
            response = await self._make_request("reports/revenue", params=params)
            return response.get("report", {})
        except Exception as e:
            return {}
