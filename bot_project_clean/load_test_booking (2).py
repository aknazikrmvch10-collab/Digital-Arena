"""
Load Testing Script for Restaurant/Computer Club Booking System
Simulates 50 concurrent users attempting to book the same time slot (19:00)
to detect race conditions and measure system performance.

Requirements:
    pip install locust

Usage:
    # Run with 50 concurrent users
    locust -f load_test_booking.py --host=http://localhost:8000 --users 50 --spawn-rate 10 --run-time 2m
    
    # Run with web UI
    locust -f load_test_booking.py --host=http://localhost:8000
    # Then open http://localhost:8089
"""

from locust import HttpUser, task, between, events
from datetime import datetime, timedelta
import random
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Track booking results for analysis
booking_results = {
    "success": 0,
    "conflict": 0,
    "error": 0,
    "duplicate_check": []
}


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops - analyze results."""
    logger.info("=" * 60)
    logger.info("LOAD TEST RESULTS SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Successful bookings: {booking_results['success']}")
    logger.info(f"Booking conflicts: {booking_results['conflict']}")
    logger.info(f"Errors: {booking_results['error']}")
    
    # Check for potential race conditions
    if len(booking_results['duplicate_check']) > 0:
        logger.warning("POTENTIAL RACE CONDITION DETECTED!")
        logger.warning(f"Multiple bookings for same slot: {booking_results['duplicate_check']}")
    
    logger.info("=" * 60)
    logger.info("RECOMMENDATIONS:")
    if booking_results['success'] > 10:
        logger.warning("CRITICAL: More than 10 successful bookings for same slot!")
        logger.warning("    This indicates a race condition vulnerability.")
        logger.warning("    Expected: Only 1-2 successful bookings (one per computer)")
    else:
        logger.info("Race condition protection appears to be working.")
    
    logger.info("=" * 60)


class BookingUser(HttpUser):
    """Simulates a user browsing and booking."""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between requests
    
    def on_start(self):
        """Called when a user starts - initialize user data."""
        self.user_id = random.randint(100000, 999999)
        self.club_id = 1  # Target club ID (change if needed)
        self.computer_id = None
        
        logger.info(f"User {self.user_id} started")
    
    @task(3)
    def view_clubs(self):
        """Simulate viewing club list."""
        with self.client.get("/api/clubs", catch_response=True) as response:
            if response.status_code == 200:
                clubs = response.json()
                if len(clubs) > 0:
                    self.club_id = clubs[0]['id']
                    response.success()
                else:
                    response.failure("No clubs found")
            else:
                response.failure(f"Failed to load clubs: {response.status_code}")
    
    @task(5)
    def view_computers(self):
        """Simulate viewing computers/tables."""
        with self.client.get(
            f"/api/clubs/{self.club_id}/computers",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                computers = response.json()
                if len(computers) > 0:
                    # Pick a random computer
                    self.computer_id = random.choice(computers)['id']
                    response.success()
                else:
                    response.failure("No computers found")
            else:
                response.failure(f"Failed to load computers: {response.status_code}")
    
    @task(2)
    def check_availability(self):
        """Simulate checking availability."""
        if not self.computer_id:
            return
        
        date = datetime.now().strftime("%Y-%m-%d")
        
        with self.client.get(
            f"/api/availability?club_id={self.club_id}&computer_id={self.computer_id}&date={date}",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                occupied_hours = data.get('occupied_hours', [])
                logger.debug(f"Occupied hours for PC {self.computer_id}: {occupied_hours}")
                response.success()
            else:
                response.failure(f"Failed to check availability: {response.status_code}")
    
    @task(10)  # HIGHEST PRIORITY: Most users will try to book
    def create_booking_at_7pm(self):
        """
        Simulate creating a booking at 19:00 (7 PM).
        This is the CRITICAL test for race conditions.
        """
        if not self.computer_id:
            # If no computer selected, pick one
            self.view_computers()
            if not self.computer_id:
                return
        
        # Target time: Today at 19:00
        start_time = datetime.now().replace(hour=19, minute=0, second=0, microsecond=0)
        
        # If 19:00 has passed, book for tomorrow
        if start_time < datetime.now():
            start_time += timedelta(days=1)
        
        payload = {
            "user_id": self.user_id,
            "club_id": self.club_id,
            "computer_id": str(self.computer_id),
            "start_time": start_time.isoformat(),
            "duration_minutes": 60
        }
        
        with self.client.post(
            "/api/bookings",
            json=payload,
            catch_response=True,
            name="/api/bookings [19:00 slot]"  # Group by time slot
        ) as response:
            if response.status_code == 200:
                result = response.json()
                
                if result.get("success"):
                    booking_results["success"] += 1
                    booking_id = result.get("booking_id")
                    
                    # Track for duplicate detection
                    booking_key = f"{self.club_id}:{self.computer_id}:19:00"
                    booking_results["duplicate_check"].append({
                        "key": booking_key,
                        "booking_id": booking_id,
                        "user_id": self.user_id
                    })
                    
                    logger.info(f"User {self.user_id} successfully booked PC {self.computer_id} at 19:00 (Booking #{booking_id})")
                    response.success()
                else:
                    # Booking conflict (expected for most users)
                    booking_results["conflict"] += 1
                    message = result.get("message", "Unknown conflict")
                    logger.debug(f"User {self.user_id} booking conflict: {message}")
                    response.success()  # This is expected behavior, not a failure
            else:
                booking_results["error"] += 1
                logger.error(f"User {self.user_id} booking error: {response.status_code} - {response.text}")
                response.failure(f"HTTP {response.status_code}: {response.text}")


class AggressiveBookingUser(BookingUser):
    """
    Aggressive user that spams booking requests.
    Used to stress-test race condition protection.
    """
    
    wait_time = between(0.1, 0.5)  # Very fast requests
    
    @task(20)  # Even higher priority
    def rapid_fire_booking(self):
        """Rapidly attempt to book the same slot."""
        self.create_booking_at_7pm()


class ConcurrentSameSlotUser(HttpUser):
    """
    Specialized user that ONLY books 19:00 slot on PC-1.
    This is the ultimate race condition test.
    """
    
    wait_time = between(0, 0.1)  # Almost no delay
    
    def on_start(self):
        self.user_id = random.randint(100000, 999999)
        self.club_id = 1
        self.computer_id = "1"  # Always target PC-1
    
    @task
    def book_pc1_at_7pm(self):
        """Book PC-1 at 19:00 - race condition stress test."""
        start_time = datetime.now().replace(hour=19, minute=0, second=0, microsecond=0)
        if start_time < datetime.now():
            start_time += timedelta(days=1)
        
        payload = {
            "user_id": self.user_id,
            "club_id": self.club_id,
            "computer_id": self.computer_id,
            "start_time": start_time.isoformat(),
            "duration_minutes": 60
        }
        
        with self.client.post("/api/bookings", json=payload, catch_response=True) as response:
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    booking_results["success"] += 1
                    logger.warning(f"User {self.user_id} got PC-1 at 19:00! (Booking #{result.get('booking_id')})")
                    response.success()
                else:
                    booking_results["conflict"] += 1
                    response.success()
            else:
                booking_results["error"] += 1
                response.failure(f"HTTP {response.status_code}")


# Default user class
# To run different scenarios, use:
# locust -f load_test_booking.py BookingUser
# locust -f load_test_booking.py AggressiveBookingUser
# locust -f load_test_booking.py ConcurrentSameSlotUser
