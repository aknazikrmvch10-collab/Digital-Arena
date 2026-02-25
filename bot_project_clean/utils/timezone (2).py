"""
Timezone utility for CyberArena.
All business logic MUST use these helpers instead of datetime.now() or datetime.utcnow().
"""
from datetime import datetime, timezone, timedelta

# Tashkent is UTC+5 (no DST)
TASHKENT_TZ = timezone(timedelta(hours=5))


def now_tashkent() -> datetime:
    """Get current time in Tashkent timezone (aware datetime)."""
    return datetime.now(TASHKENT_TZ)


def to_tashkent(dt: datetime) -> datetime:
    """Convert a datetime to Tashkent timezone.
    If naive (no tzinfo), assumes it IS already Tashkent time and just attaches the tz.
    If aware, converts it.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=TASHKENT_TZ)
    return dt.astimezone(TASHKENT_TZ)


def make_naive_tashkent(dt: datetime) -> datetime:
    """Strip timezone info after ensuring it's in Tashkent.
    Use this when storing to DB or comparing with naive datetimes from DB.
    """
    return to_tashkent(dt)
