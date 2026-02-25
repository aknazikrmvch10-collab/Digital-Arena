import asyncio
from database import async_session_factory
from models import Club, Computer
from sqlalchemy import select, func

async def add_computers():
    async with async_session_factory() as session:
        # Check all clubs
        result = await session.execute(select(Club))
        clubs = result.scalars().all()
        
        for club in clubs:
            # Count existing PCs
            count_result = await session.execute(
                select(func.count(Computer.id)).where(Computer.club_id == club.id)
            )
            count = count_result.scalar()
            
            if count == 0:
                print(f"Adding 10 computers to Club {club.name} (id={club.id})...")
                # Add 10 Standard PCs
                for i in range(1, 11):
                    pc = Computer(
                        club_id=club.id,
                        zone="standart",
                        name=f"PC-{i}",
                        price_per_hour=15000,
                        # is_available - likely not a column or computed
                        gpu="RTX 3060",
                        ram_gb=16,
                        monitor_hz=144
                    )
                    session.add(pc)
                await session.commit()
                print("Done!")
            else:
                print(f"Skipping {club.name} (id={club.id}): already has {count} computers.")

if __name__ == "__main__":
    asyncio.run(add_computers())
