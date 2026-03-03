"""
seed_zone_photos.py — Populate ClubZoneSetting with photos and descriptions for DEMO.
Run once: python seed_zone_photos.py
"""
import asyncio
from database import async_session_factory
from models import Club, ClubZoneSetting
from sqlalchemy import select

ZONE_DATA = {
    "VIP": {
        "image_url": "https://images.unsplash.com/photo-1542751371-adc38448a05e?auto=format&fit=crop&w=1200&q=80",
        "description": "🌟 <b>VIP зона</b>\n\nПремиальные кресла с подогревом, RTX 4090, 4K 144Hz мониторы.\nПерсональный сервис и тихая атмосфера."
    },
    "Standard": {
        "image_url": "https://images.unsplash.com/photo-1587202372775-e229f172b9d7?auto=format&fit=crop&w=1200&q=80",
        "description": "💻 <b>Standard зона</b>\n\nМощные игровые ПК с RTX 3060, 144Hz мониторы.\nКомфортные кресла AKRACING. Лучшее соотношение цена/качество."
    },
    "Bootcamp": {
        "image_url": "https://images.unsplash.com/photo-1598550476439-6847785fcea6?auto=format&fit=crop&w=1200&q=80",
        "description": "🎮 <b>Bootcamp зона</b>\n\nЗаточена под турниры и командную игру.\nRTX 3070, 240Hz мониторы, игровые периферии Razer.\nИдеально для соревновательного гейминга."
    },
}

async def seed():
    async with async_session_factory() as session:
        # Get all clubs
        result = await session.execute(select(Club))
        clubs = result.scalars().all()
        
        if not clubs:
            print("❌ No clubs found. Please run setup_club.py first.")
            return
        
        count = 0
        for club in clubs:
            for zone_name, data in ZONE_DATA.items():
                # Check if already seeded
                existing = await session.execute(
                    select(ClubZoneSetting).where(
                        ClubZoneSetting.club_id == club.id,
                        ClubZoneSetting.zone_name == zone_name
                    )
                )
                if existing.scalars().first():
                    print(f"  ⏭ Club {club.name} / Zone {zone_name}: already seeded, skipping.")
                    continue
                
                setting = ClubZoneSetting(
                    club_id=club.id,
                    zone_name=zone_name,
                    image_url=data["image_url"],
                    description=data["description"],
                )
                session.add(setting)
                count += 1
                print(f"  ✅ Club {club.name} / Zone {zone_name}: added.")
        
        await session.commit()
        print(f"\n🎉 Done! Added {count} zone settings.")

if __name__ == "__main__":
    asyncio.run(seed())
