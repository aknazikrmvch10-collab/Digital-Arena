import asyncio
from database import async_session_factory
from models import Club, Computer
from sqlalchemy import select, func

async def check_clubs():
    async with async_session_factory() as session:
        # Get all clubs
        result = await session.execute(select(Club))
        clubs = result.scalars().all()
        print(f"Total Clubs: {len(clubs)}")
        
        for club in clubs:
            # Count computers for each club
            count_result = await session.execute(
                select(func.count(Computer.id)).where(Computer.club_id == club.id)
            )
            count = count_result.scalar()
            print(f"  Club {club.id} ({club.name}, type={club.venue_type}): {count} computers")

if __name__ == "__main__":
    asyncio.run(check_clubs())
