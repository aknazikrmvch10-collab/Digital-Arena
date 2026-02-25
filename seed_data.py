from sqlalchemy import select
from models import Club, Computer
from database import async_session_factory

async def seed_test_clubs():
    """Creates 3 test clubs if they don't already exist."""
    
    async with async_session_factory() as session:
        # Check if clubs exist
        result = await session.execute(select(Club))
        existing = result.scalars().all()
        
        if len(existing) > 0:
            print(f"Database already has {len(existing)} clubs. Skipping seed.")
            return
        
        # Create Club 1: Mock Driver (for testing UI)
        club1 = Club(
            name="CyberTest Arena",
            city="Tashkent",
            address="Yunusabad District, Amir Temur 120",
            latitude=41.3123,
            longitude=69.2787,
            driver_type="MOCK",
            connection_config={},
            is_active=True
        )
        session.add(club1)
        
        # Create Club 2: Standalone (with basic computers)
        club2 = Club(
            name="LocalClub Gaming",
            city="Samarkand",
            address="Registan Square, Building 5",
            latitude=39.6547,
            longitude=66.9750,
            driver_type="STANDALONE",
            connection_config={},
            is_active=True
        )
        session.add(club2)
        
        # Create Club 3: ProGaming Arena (with detailed specs)
        club3 = Club(
            name="ProGaming Arena",
            city="Tashkent",
            address="Chilanzar District, Bunyodkor Avenue 7",
            latitude=41.2756,
            longitude=69.2036,
            driver_type="STANDALONE",
            connection_config={},
            is_active=True
        )
        session.add(club3)
        
        await session.commit()
        await session.refresh(club1)
        await session.refresh(club2)
        await session.refresh(club3)
        
        # Add basic computers for Club 2
        for i in range(1, 6):
            pc = Computer(
                club_id=club2.id,
                name=f"PC-{i}",
                zone="Standard" if i <= 3 else "VIP",
                is_active=True
            )
            session.add(pc)
        
        # Add detailed computers for Club 3 (ProGaming Arena)
        
        # Budget Tier: 4 PCs (Standard Zone)
        for i in range(1, 5):
            pc = Computer(
                club_id=club3.id,
                name=f"PC-{i}",
                zone="Standard",
                cpu="Intel i3-10100",
                gpu="GTX 1050 Ti",
                ram_gb=8,
                monitor_hz=60,
                price_per_hour=10000,
                is_active=True
            )
            session.add(pc)
        
        # Mid Tier: 4 PCs (VIP Zone)
        for i in range(5, 9):
            pc = Computer(
                club_id=club3.id,
                name=f"PC-{i}",
                zone="VIP",
                cpu="Intel i5-12400",
                gpu="RTX 3060",
                ram_gb=16,
                monitor_hz=144,
                price_per_hour=15000,
                is_active=True
            )
            session.add(pc)
        
        # Premium Tier: 4 PCs (Pro Zone)
        for i in range(9, 13):
            pc = Computer(
                club_id=club3.id,
                name=f"PC-{i}",
                zone="Pro",
                cpu="Intel i7-13700K",
                gpu="RTX 4070",
                ram_gb=32,
                monitor_hz=240,
                price_per_hour=25000,
                is_active=True
            )
            session.add(pc)
        
        await session.commit()
        print("Seeded 3 test clubs (CyberTest, LocalClub, ProGaming) with computers.")
