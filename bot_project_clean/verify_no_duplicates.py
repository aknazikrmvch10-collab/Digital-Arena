"""
Verification Script: Check for Duplicate Bookings (Race Condition Detection)

This script checks the database for overlapping bookings on the same computer,
which would indicate a race condition vulnerability.

Usage:
    python verify_no_duplicates.py
"""

import asyncio
import logging
from sqlalchemy import text
from database import engine
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def check_duplicate_bookings():
    """Check for overlapping bookings that indicate race conditions."""
    
    logger.info("=" * 60)
    logger.info("RACE CONDITION VERIFICATION")
    logger.info("=" * 60)
    logger.info(f"Checking database at: {datetime.now()}")
    logger.info("")
    
    async with engine.connect() as conn:
        # Query 1: Find exact duplicate bookings (same time, same computer)
        logger.info("1. Checking for exact duplicate bookings...")
        result = await conn.execute(text("""
            SELECT 
                club_id,
                computer_name,
                start_time,
                end_time,
                COUNT(*) as booking_count,
                GROUP_CONCAT(id) as booking_ids,
                GROUP_CONCAT(user_id) as user_ids
            FROM bookings
            WHERE status IN ('CONFIRMED', 'ACTIVE')
            GROUP BY club_id, computer_name, start_time, end_time
            HAVING COUNT(*) > 1
            ORDER BY start_time DESC;
        """))
        
        duplicates = result.fetchall()
        
        if duplicates:
            logger.error(f"🔴 CRITICAL: Found {len(duplicates)} duplicate booking(s)!")
            logger.error("")
            for dup in duplicates:
                logger.error(f"  Club ID: {dup[0]}")
                logger.error(f"  Computer: {dup[1]}")
                logger.error(f"  Time: {dup[2]} - {dup[3]}")
                logger.error(f"  Booking Count: {dup[4]}")
                logger.error(f"  Booking IDs: {dup[5]}")
                logger.error(f"  User IDs: {dup[6]}")
                logger.error("")
        else:
            logger.info("OK: No exact duplicate bookings found")
        
        # Query 2: Find overlapping bookings (different times but overlap)
        logger.info("")
        logger.info("2. Checking for overlapping bookings...")
        result = await conn.execute(text("""
            SELECT 
                b1.id as booking1_id,
                b1.user_id as user1_id,
                b1.computer_name,
                b1.start_time as start1,
                b1.end_time as end1,
                b2.id as booking2_id,
                b2.user_id as user2_id,
                b2.start_time as start2,
                b2.end_time as end2
            FROM bookings b1
            JOIN bookings b2 ON 
                b1.club_id = b2.club_id 
                AND b1.computer_name = b2.computer_name
                AND b1.id < b2.id
                AND b1.status IN ('CONFIRMED', 'ACTIVE')
                AND b2.status IN ('CONFIRMED', 'ACTIVE')
                AND b1.start_time < b2.end_time
                AND b1.end_time > b2.start_time
            ORDER BY b1.start_time DESC
            LIMIT 50;
        """))
        
        overlaps = result.fetchall()
        
        if overlaps:
            logger.error(f"🔴 CRITICAL: Found {len(overlaps)} overlapping booking(s)!")
            logger.error("")
            for overlap in overlaps[:10]:  # Show first 10
                logger.error(f"  Computer: {overlap[2]}")
                logger.error(f"  Booking 1: ID={overlap[0]}, User={overlap[1]}, {overlap[3]} - {overlap[4]}")
                logger.error(f"  Booking 2: ID={overlap[5]}, User={overlap[6]}, {overlap[7]} - {overlap[8]}")
                logger.error("")
            
            if len(overlaps) > 10:
                logger.error(f"  ... and {len(overlaps) - 10} more overlaps")
        else:
            logger.info("OK: No overlapping bookings found")
        
        # Query 3: Statistics
        logger.info("")
        logger.info("3. Booking statistics...")
        result = await conn.execute(text("""
            SELECT 
                status,
                COUNT(*) as count
            FROM bookings
            GROUP BY status
            ORDER BY count DESC;
        """))
        
        stats = result.fetchall()
        logger.info("Bookings by status:")
        for stat in stats:
            logger.info(f"  {stat[0]}: {stat[1]}")
        
        # Query 4: Recent bookings
        logger.info("")
        logger.info("4. Recent bookings (last 10)...")
        result = await conn.execute(text("""
            SELECT 
                id,
                club_id,
                computer_name,
                user_id,
                start_time,
                end_time,
                status,
                created_at
            FROM bookings
            ORDER BY created_at DESC
            LIMIT 10;
        """))
        
        recent = result.fetchall()
        for booking in recent:
            logger.info(f"  ID={booking[0]}, PC={booking[2]}, User={booking[3]}, {booking[4]} - {booking[5]}, Status={booking[6]}")
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("VERIFICATION SUMMARY")
    logger.info("=" * 60)
    
    total_issues = len(duplicates) + len(overlaps)
    
    if total_issues == 0:
        logger.info("PASSED: No race condition issues detected!")
        logger.info("")
        logger.info("Your booking system appears to be handling concurrent")
        logger.info("requests correctly. No duplicate or overlapping bookings found.")
        return True
    else:
        logger.error(f"❌ FAILED: Found {total_issues} race condition issue(s)!")
        logger.error("")
        logger.error("RECOMMENDED ACTIONS:")
        logger.error("1. Review the technical_audit_report.md for fixes")
        logger.error("2. Implement transaction isolation in handlers/api.py")
        logger.error("3. Add row-level locking with with_for_update=True")
        logger.error("4. Re-run load tests after fixes")
        logger.error("")
        logger.error("IMMEDIATE ACTION:")
        logger.error("If this is production, consider:")
        logger.error("- Temporarily disabling concurrent bookings")
        logger.error("- Manually reviewing and fixing duplicate bookings")
        logger.error("- Deploying race condition fixes ASAP")
        return False


async def main():
    try:
        success = await check_duplicate_bookings()
        
        logger.info("=" * 60)
        
        if success:
            exit(0)  # Success
        else:
            exit(1)  # Failure - issues found
            
    except Exception as e:
        logger.error("")
        logger.error("=" * 60)
        logger.error("❌ VERIFICATION FAILED!")
        logger.error("=" * 60)
        logger.error(f"Error: {e}", exc_info=True)
        exit(2)  # Error


if __name__ == "__main__":
    print("=" * 60)
    print("Race Condition Verification")
    print("=" * 60)
    print("")
    print("This script will check your database for:")
    print("- Duplicate bookings (exact same time/computer)")
    print("- Overlapping bookings (different times but conflict)")
    print("")
    
    asyncio.run(main())
