"""
Timezone utility for Digital Arena.
All business logic MUST use these helpers instead of datetime.now() or datetime.utcnow().

Conventions:
  - DB stores datetimes as NAIVE UTC (no tzinfo).
  - Use now_utc() for comparisons against DB values in background tasks.
  - Use now_tashkent() for displaying to users and business rules in Tashkent time.
  - Use to_tashkent() to convert UTC storage values to display values.
"""
from datetime import datetime, timezone, timedelta

# Tashkent is UTC+5 (no DST)
TASHKENT_TZ = timezone(timedelta(hours=5))
UTC_TZ = timezone.utc


def now_tashkent() -> datetime:
    """Get current datetime in Tashkent timezone (UTC+5), aware."""
    return datetime.now(TASHKENT_TZ)


def now_utc() -> datetime:
    """Get current datetime in UTC, naive (matches DB storage format).
    Use this when comparing against DB-stored datetimes in background tasks."""
    return datetime.utcnow()  # naive UTC — matches how we store in DB


def to_tashkent(dt: datetime) -> datetime:
    """Convert a datetime to Tashkent timezone (for display).
    If naive: assumes it is stored as UTC (our DB convention) and converts to Tashkent.
    If aware: converts it normally.
    """
    if dt.tzinfo is None:
        # Assume naive = UTC (our DB convention)
        return dt.replace(tzinfo=UTC_TZ).astimezone(TASHKENT_TZ)
    return dt.astimezone(TASHKENT_TZ)


def make_naive_utc(dt: datetime) -> datetime:
    """Convert any datetime to naive UTC — use before storing to DB."""
    if dt.tzinfo is None:
        return dt  # already naive, assume UTC
    return dt.astimezone(UTC_TZ).replace(tzinfo=None)


def make_naive_tashkent(dt: datetime) -> datetime:
    """DEPRECATED: Use to_tashkent() + make_naive_utc() instead.
    Strip timezone info after ensuring it's in Tashkent.
    """
    return to_tashkent(dt).replace(tzinfo=None)

