from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, JSON, Float, BigInteger
from sqlalchemy.orm import relationship
from database import Base
from utils.timezone import now_tashkent

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    tg_id = Column(BigInteger, unique=True, index=True)
    username = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: now_tashkent())
    
    # Notification settings
    notifications_enabled = Column(Boolean, default=True)  # Enable/disable notifications
    notification_minutes = Column(Integer, default=30)  # 15, 30, or 60 minutes before
    
    # Age verification
    age_confirmed = Column(Boolean, default=False)  # User confirmed they are 18+
    
    # Referral system
    referral_code = Column(String, unique=True, nullable=True, index=True)  # This user's referral code
    referred_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Who referred this user
    referral_bonus_used = Column(Boolean, default=False)  # Has their first booking bonus been applied

    bookings = relationship("Booking", back_populates="user")
    reviews = relationship("Review", foreign_keys="Review.user_id", back_populates="user")

class Club(Base):
    __tablename__ = "clubs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    city = Column(String, index=True)
    address = Column(String)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # Type of establishment
    venue_type = Column(String, default="computer_club") # "computer_club", "restaurant"

    # Driver Configuration
    driver_type = Column(String) # "SMARTSHELL", "ICAFE", "STANDALONE", "MOCK"
    connection_config = Column(JSON, default={}) # API Keys, URLs, etc.
    
    # Contact and info
    admin_phone = Column(String, nullable=True)
    working_hours = Column(String, nullable=True, default="24/7")
    description = Column(String, nullable=True)  # Short description for club card
    image_url = Column(String, nullable=True)  # Club photo URL
    wifi_speed = Column(String, nullable=True)  # e.g. "500 Mbps"
    
    # Club admin Telegram IDs (comma-separated)
    club_admin_tg_ids = Column(String, nullable=True)  # "123456,789012"

    is_active = Column(Boolean, default=True)
    
    bookings = relationship("Booking", back_populates="club")
    computers = relationship("Computer", back_populates="club") # For Computer Clubs
    tables = relationship("RestaurantTable", back_populates="club") # For Restaurants
    reviews = relationship("Review", back_populates="club")
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "city": self.city,
            "address": self.address,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "venue_type": self.venue_type,
            "driver_type": self.driver_type,
            "admin_phone": self.admin_phone,
            "working_hours": self.working_hours,
            "description": self.description,
            "image_url": self.image_url,
            "wifi_speed": self.wifi_speed,
            "is_active": self.is_active
        }

class Computer(Base):
    __tablename__ = "computers"
    
    id = Column(Integer, primary_key=True, index=True)
    club_id = Column(Integer, ForeignKey("clubs.id"))
    name = Column(String)  # "PC-1", "VIP-5"
    zone = Column(String)  # "Standard", "VIP", "Pro"
    
    # Hardware specifications
    cpu = Column(String, nullable=True)
    gpu = Column(String, nullable=True)
    ram_gb = Column(Integer, nullable=True)
    monitor_hz = Column(Integer, nullable=True)
    price_per_hour = Column(Integer, nullable=True)
    image_url = Column(String, nullable=True) 

    is_active = Column(Boolean, default=True)

    club = relationship("Club", back_populates="computers")
    
    def to_dict(self):
        return {
            "id": self.id,
            "club_id": self.club_id,
            "name": self.name,
            "zone": self.zone,
            "cpu": self.cpu,
            "gpu": self.gpu,
            "ram_gb": self.ram_gb,
            "monitor_hz": self.monitor_hz,
            "price_per_hour": self.price_per_hour,
            "image_url": self.image_url,
            "is_active": self.is_active,
            "type": "computer"
        }

class RestaurantTable(Base):
    __tablename__ = "restaurant_tables"
    
    id = Column(Integer, primary_key=True, index=True)
    club_id = Column(Integer, ForeignKey("clubs.id"))
    name = Column(String) # "Table 1", "Booth 2"
    zone = Column(String) # "Main Hall", "Terrace", "VIP Room"
    
    seats = Column(Integer, default=4)
    position = Column(String, nullable=True) # "Window", "Center", "Corner"
    
    min_deposit = Column(Integer, default=0) # Minimum spend/deposit
    booking_price = Column(Integer, default=0) # Price just to book
    
    image_url = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    
    club = relationship("Club", back_populates="tables")
    
    def to_dict(self):
        return {
            "id": self.id,
            "club_id": self.club_id,
            "name": self.name,
            "zone": self.zone,
            "seats": self.seats,
            "position": self.position,
            "min_deposit": self.min_deposit,
            "booking_price": self.booking_price,
            "image_url": self.image_url,
            "is_active": self.is_active,
            "type": "table"
        }

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    club_id = Column(Integer, ForeignKey("clubs.id"), nullable=False)
    computer_name = Column(String, nullable=False) # Name of the item (PC or Table)
    item_id = Column(Integer, nullable=True) # ID of Computer or RestaurantTable
    start_time = Column(DateTime(timezone=True), nullable=False, index=True)  # ✅ FIX #9: added index for availability queries
    end_time = Column(DateTime(timezone=True), nullable=False, index=True)    # ✅ FIX #9: added index for availability queries
    status = Column(String, default="CONFIRMED")
    confirmation_code = Column(String, nullable=True) # Unique code for check-in
    check_timeout = Column(Boolean, default=False)
    notification_sent = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: now_tashkent())

    user = relationship("User", back_populates="bookings")
    club = relationship("Club", back_populates="bookings")

class Admin(Base):
    __tablename__ = "admins"
    id = Column(Integer, primary_key=True, index=True)
    tg_id = Column(BigInteger, unique=True, nullable=False)
    club_id = Column(Integer, ForeignKey("clubs.id"), nullable=True)  # None = super-admin
    created_at = Column(DateTime(timezone=True), default=lambda: now_tashkent())

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: now_tashkent(), index=True)
    event_type = Column(String, index=True)  # e.g., "BOOKING_CREATED", "PC_USAGE_LOG"
    details = Column(JSON)  # Stores the actual log data
    previous_hash = Column(String, nullable=True)  # Hash of the previous record (chain)
    hash = Column(String)  # Hash of this record (SHA256)

    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "event_type": self.event_type,
            "details": self.details,
            "previous_hash": self.previous_hash,
            "hash": self.hash
        }


class Review(Base):
    """User review of a booking/club after it's completed."""
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    club_id = Column(Integer, ForeignKey("clubs.id"), nullable=False)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False, unique=True)  # One review per booking
    rating = Column(Integer, nullable=False)  # 1-5 stars
    comment = Column(String, nullable=True)  # Optional text review
    created_at = Column(DateTime(timezone=True), default=lambda: now_tashkent())

    user = relationship("User", foreign_keys=[user_id], back_populates="reviews")
    club = relationship("Club", back_populates="reviews")
