from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, JSON, Float, BigInteger
from sqlalchemy.orm import relationship
from database import Base
from utils.timezone import now_tashkent, now_utc

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    tg_id = Column(BigInteger, unique=True, index=True)
    username = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: now_utc())
    
    # Notification settings
    notifications_enabled = Column(Boolean, default=True)
    notification_minutes = Column(Integer, default=30)
    
    # Age verification
    age_confirmed = Column(Boolean, default=False)
    
    # Language preference: 'ru', 'uz', 'kz'
    language = Column(String, default='ru', nullable=False)
    
    # Referral system
    referral_code = Column(String, unique=True, nullable=True, index=True)
    referred_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    referral_bonus_used = Column(Boolean, default=False)
    
    # Loyalty and Finance
    loyalty_level = Column(String, default="Начинающий") # Начинающий, Продвинутый, Pro
    bonus_points = Column(Integer, default=0) # Accumulated cashback points
    balance = Column(Integer, default=0) # Real money balance deposited

    # Password-based auth (for multi-device login without Telegram)
    password_hash = Column(String, nullable=True)

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
    connection_config = Column(JSON, default=dict)  # API Keys, URLs, etc.
    
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

class ClubZoneSetting(Base):
    """Custom settings (like photos and descriptions) for a specific zone in a club"""
    __tablename__ = "club_zone_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    club_id = Column(Integer, ForeignKey("clubs.id"), nullable=False, index=True)
    zone_name = Column(String, nullable=False, index=True)
    image_url = Column(String, nullable=True)
    description = Column(String, nullable=True)
    
    club = relationship("Club", foreign_keys=[club_id])

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
    
    # Financials and Loyalty
    total_price = Column(Integer, nullable=True)     # Final price after discounts
    discount_amount = Column(Integer, default=0)     # Amount discounted by promo
    earned_points = Column(Integer, default=0)       # Cashback points to be awarded on completion
    
    created_at = Column(DateTime(timezone=True), default=lambda: now_utc())

    user = relationship("User", back_populates="bookings")
    club = relationship("Club", back_populates="bookings")

class Admin(Base):
    __tablename__ = "admins"
    id = Column(Integer, primary_key=True, index=True)
    tg_id = Column(BigInteger, unique=True, nullable=False)
    club_id = Column(Integer, ForeignKey("clubs.id"), nullable=True)  # None = super-admin
    created_at = Column(DateTime(timezone=True), default=lambda: now_utc())

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: now_utc(), index=True)
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
    created_at = Column(DateTime(timezone=True), default=lambda: now_utc())

    user = relationship("User", foreign_keys=[user_id], back_populates="reviews")
    club = relationship("Club", back_populates="reviews")


class PromoCode(Base):
    """Promotional codes for discounts on bookings."""
    __tablename__ = "promo_codes"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, nullable=False, index=True)  # e.g. 'ARENA20'
    discount_percent = Column(Integer, default=10)  # 10 = 10% off
    max_uses = Column(Integer, nullable=True)  # None = unlimited
    uses_count = Column(Integer, default=0)  # How many times used
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # None = no expiry
    club_id = Column(Integer, ForeignKey("clubs.id"), nullable=True)  # None = platform-wide
    created_at = Column(DateTime(timezone=True), default=lambda: now_utc())
    created_by_tg_id = Column(BigInteger, nullable=True)  # Telegram ID of the creator

    def is_valid(self) -> bool:
        from utils.timezone import now_utc
        if not self.is_active:
            return False
        if self.max_uses and self.uses_count >= self.max_uses:
            return False
        # Compare using naive UTC to match DB storage convention
        now = now_utc()
        expires = self.expires_at.replace(tzinfo=None) if self.expires_at and self.expires_at.tzinfo else self.expires_at
        if expires and now > expires:
            return False
        return True


# ====================== PWA PHONE AUTH ======================

class AppAuthCode(Base):
    """Temporary code sent via Telegram bot for standalone PWA login."""
    __tablename__ = "app_auth_codes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, nullable=False, index=True)   # Telegram user ID
    phone = Column(String, nullable=False)                      # Phone number (e.g. +998901234567)
    code = Column(String(6), nullable=False)                    # 6-digit code
    created_at = Column(DateTime(timezone=True), default=lambda: now_utc())
    expires_at = Column(DateTime(timezone=True), nullable=False) # 10 min TTL
    used = Column(Boolean, default=False)


class AppSession(Base):
    """Active session token for a standalone PWA user."""
    __tablename__ = "app_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, nullable=False, index=True)    # Telegram user ID
    session_token = Column(String, unique=True, index=True)     # UUID token
    phone = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: now_utc())
    last_seen = Column(DateTime(timezone=True), default=lambda: now_utc())


# ====================== PAYMENTS ======================

class Payment(Base):
    """Payment record for a booking."""
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Integer, nullable=False)              # Amount in UZS (сум)
    currency = Column(String, default="UZS")

    # Payment provider: "test", "click", "payme"
    provider = Column(String, default="test", nullable=False)
    # External transaction ID from Click/Payme
    transaction_id = Column(String, nullable=True, index=True)

    # Status: "pending", "paid", "failed", "refunded"
    status = Column(String, default="pending", nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: now_utc())
    paid_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User")
    booking = relationship("Booking")


# ====================== PWA BAR (SNACKS & DRINKS) ======================

class BarItem(Base):
    """Items available for order to the PC."""
    __tablename__ = "bar_items"

    id = Column(Integer, primary_key=True, index=True)
    club_id = Column(Integer, ForeignKey("clubs.id"), nullable=True) # None = all clubs in chain
    name = Column(String, nullable=False)
    category = Column(String, default="Напитки") # e.g. Напитки, Снеки, Горячее
    price = Column(Integer, nullable=False)
    image_url = Column(String, nullable=True)
    is_available = Column(Boolean, default=True)

    club = relationship("Club")


class BarOrder(Base):
    """An order placed by a user to be delivered to their PC."""
    __tablename__ = "bar_orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    club_id = Column(Integer, ForeignKey("clubs.id"), nullable=False)
    pc_name = Column(String, nullable=False) # e.g. "VIP-5"
    items = Column(JSON, nullable=False)     # list of dicts: [{"id": 1, "name": "Cola", "qty": 2, "price": 10000}]
    total_price = Column(Integer, nullable=False)
    status = Column(String, default="NEW")   # "NEW", "DELIVERED", "CANCELLED"
    created_at = Column(DateTime(timezone=True), default=lambda: now_utc())

    user = relationship("User")
    club = relationship("Club")


# ====================== ICAFE AUDIT MODULE ======================

class IcafeSession(Base):
    """Raw session data synced from iCafe Cloud API for audit purposes."""
    __tablename__ = "icafe_sessions"

    id = Column(Integer, primary_key=True, index=True)
    club_id = Column(Integer, ForeignKey("clubs.id"), nullable=False, index=True)
    # iCafe Cloud identifiers
    icafe_session_id = Column(String, nullable=False, index=True)  # iCafe's own session ID
    icafe_pc_id = Column(String, nullable=False, index=True)        # PC ID in iCafe
    icafe_pc_name = Column(String, nullable=True)                   # PC Name (e.g. "PC-7")
    # Session timing
    start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    end_time = Column(DateTime(timezone=True), nullable=True)       # Null if still active
    duration_minutes = Column(Integer, nullable=True)
    # Financial data from iCafe
    icafe_price = Column(Integer, nullable=True)                    # Price charged by iCafe (UZS)
    icafe_paid = Column(Integer, nullable=True)                     # Amount actually paid in iCafe
    # Raw data snapshot
    raw_data = Column(JSON, nullable=True)                          # Full raw JSON from iCafe
    # Sync metadata
    synced_at = Column(DateTime(timezone=True), default=lambda: now_utc())

    club = relationship("Club")

    def to_dict(self):
        return {
            "id": self.id,
            "club_id": self.club_id,
            "icafe_session_id": self.icafe_session_id,
            "icafe_pc_id": self.icafe_pc_id,
            "icafe_pc_name": self.icafe_pc_name,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_minutes": self.duration_minutes,
            "icafe_price": self.icafe_price,
            "icafe_paid": self.icafe_paid,
            "synced_at": self.synced_at.isoformat() if self.synced_at else None,
        }


class AuditDiscrepancy(Base):
    """
    Detected mismatch between Digital Arena booking and iCafe session data.
    This is the core of the shadow economy detection module.
    """
    __tablename__ = "audit_discrepancies"

    id = Column(Integer, primary_key=True, index=True)
    club_id = Column(Integer, ForeignKey("clubs.id"), nullable=False, index=True)
    detected_at = Column(DateTime(timezone=True), default=lambda: now_utc(), index=True)

    # Type of discrepancy
    # Possible values:
    #   "UNREGISTERED_SESSION"  - iCafe session has no matching DA booking
    #   "PAYMENT_MISMATCH"      - Booking exists in DA but price differs from iCafe
    #   "BOOKING_NO_SESSION"    - DA booking confirmed but no iCafe session found
    #   "DURATION_MISMATCH"     - Booked duration differs significantly from actual
    discrepancy_type = Column(String, nullable=False, index=True)

    # Reference IDs
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=True)  # DA booking (if exists)
    icafe_session_id = Column(Integer, ForeignKey("icafe_sessions.id"), nullable=True)

    # Financial impact
    da_amount = Column(Integer, nullable=True)       # Amount recorded in Digital Arena (UZS)
    icafe_amount = Column(Integer, nullable=True)    # Amount in iCafe Cloud (UZS)
    shadow_amount = Column(Integer, nullable=True)   # Estimated unregistered revenue (UZS)

    # Time data
    session_date = Column(DateTime(timezone=True), nullable=True)  # When the session occurred
    pc_name = Column(String, nullable=True)                        # Which PC

    # Resolution
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_note = Column(String, nullable=True)

    # Detailed description for the report
    description = Column(String, nullable=True)

    club = relationship("Club")

    def to_dict(self):
        return {
            "id": self.id,
            "club_id": self.club_id,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
            "discrepancy_type": self.discrepancy_type,
            "booking_id": self.booking_id,
            "da_amount": self.da_amount,
            "icafe_amount": self.icafe_amount,
            "shadow_amount": self.shadow_amount,
            "session_date": self.session_date.isoformat() if self.session_date else None,
            "pc_name": self.pc_name,
            "is_resolved": self.is_resolved,
            "description": self.description,
        }
