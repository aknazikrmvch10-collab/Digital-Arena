import asyncio
import sys
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)

async def check_driver():
    try:
        print("1. Importing modules...")
        from database import init_db, async_session_factory
        from drivers.factory import DriverFactory
        from models import User, Club
        from sqlalchemy import select
        
        print("2. Initializing DB...")
        await init_db()
        
        print("3. Getting a user...")
        async with async_session_factory() as session:
            # Create dummy user if needed
            user = User(tg_id=123456789, username="test_user", full_name="Test User")
            session.add(user)
            try:
                await session.commit()
            except:
                await session.rollback()
                # User exists
                from sqlalchemy import select
                result = await session.execute(select(User).where(User.tg_id == 123456789))
                user = result.scalars().first()
                
            print(f"   User ID: {user.id}")
            
            # Get club
            result = await session.execute(select(Club).limit(1))
            club = result.scalars().first()
            print(f"   Club: {club.name} (ID: {club.id}, Driver: {club.driver_type})")
            
            # Get driver
            print("4. Instantiating driver...")
            driver = DriverFactory.get_driver(club.driver_type, {"club_id": club.id, **club.connection_config})
            
            # Get computers
            print("5. Fetching computers...")
            computers = await driver.get_computers()
            print(f"   Found {len(computers)} computers")
            if not computers:
                print("   ERROR: No computers found!")
                return
            
            pc_id = computers[0].id
            print(f"   Target PC ID: {pc_id}")
            
            # Try booking
            print("6. Attempting booking...")
            start_time = datetime.now()
            result = await driver.reserve_pc(pc_id, user.id, start_time, 60)
            
            print(f"   Booking Result: {result.success}")
            print(f"   Message: {result.message}")
            if result.conflict_info:
                print(f"   Conflict: {result.conflict_info}")

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_driver())
