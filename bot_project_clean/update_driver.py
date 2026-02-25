
import asyncio
from sqlalchemy import select, update
from database import async_session_factory
from models import Club

async def main():
    async with async_session_factory() as session:
        # List current clubs
        result = await session.execute(select(Club))
        clubs = result.scalars().all()
        
        print("--- Current Clubs ---")
        for club in clubs:
            print(f"ID: {club.id} | Name: {club.name} | Driver: {club.driver_type}")
            
        # Update CyberArena Pro (or all) to MOCK
        print("\n--- Updating to MOCK ---")
        # Assuming ID 1 is the main club, but let's update by name or just update all for the demo
        target_name = "CyberArena Pro" # Replace with actual name if known, or ID 1
        
        await session.execute(
            update(Club)
            .where(Club.name.like(f"%{target_name}%"))
            .values(driver_type="MOCK")
        )
        await session.commit()
        
        # Verify
        result = await session.execute(select(Club))
        clubs = result.scalars().all()
        print("\n--- Updated Clubs ---")
        for club in clubs:
            print(f"ID: {club.id} | Name: {club.name} | Driver: {club.driver_type}")

if __name__ == "__main__":
    asyncio.run(main())
