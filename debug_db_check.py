import asyncio
from sqlalchemy import select
from models import Club, Computer
from database import async_session_factory

async def check_db():
    async with async_session_factory() as session:
        # Check Club 1 specifically
        result = await session.execute(select(Club).where(Club.id == 1))
        club = result.scalars().first()
        if club:
            print(f"\n--- CLUB 1 DETAILS ---")
            print(f"ID: {club.id}, Name: {club.name}, City: {club.city}, Driver: {club.driver_type}")
            print(f"   Config: {club.connection_config}")
        else:
            print("Club 1 not found")

if __name__ == "__main__":
    asyncio.run(check_db())
