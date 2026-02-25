"""
Migration: Add indexes on Booking.start_time and Booking.end_time
Fix #9 from audit: availability queries were doing full table scans.
Run once with: python migrate_add_booking_indexes.py
"""
import asyncio
from database import async_session_factory
from sqlalchemy import text

async def main():
    async with async_session_factory() as session:
        try:
            await session.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_bookings_start_time ON bookings (start_time)"
            ))
            await session.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_bookings_end_time ON bookings (end_time)"
            ))
            await session.commit()
            print("✅ Indexes ix_bookings_start_time and ix_bookings_end_time created successfully.")
        except Exception as e:
            print(f"❌ Error creating indexes: {e}")

if __name__ == "__main__":
    asyncio.run(main())
