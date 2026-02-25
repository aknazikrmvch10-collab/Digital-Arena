"""
Make demo data look professional for Ministry meeting.
"""
import asyncio
from database import async_session_factory
from models import Club, Computer
from sqlalchemy import select

DEMO_CLUBS = [
    {
        "id": 1,
        "name": "CyberArena Pro",
        "city": "Ташкент",
        "address": "ул. Амира Темура 120, Юнусабад",
        "latitude": 41.3123,
        "longitude": 69.2787,
    },
    {
        "id": 3,
        "name": "ProGaming Arena",
        "city": "Ташкент",
        "address": "пр. Буньодкор 7, Чиланзар",
        "latitude": 41.2756,
        "longitude": 69.2036,
    },
    {
        "id": 5,
        "name": "GG Zone",
        "city": "Самарканд",
        "address": "ул. Регистан 15",
        "latitude": 39.6547,
        "longitude": 66.9750,
    },
    {
        "id": 6,
        "name": "Pixel Hub",
        "city": "Бухара",
        "address": "ул. Навои 42",
        "latitude": 39.7745,
        "longitude": 64.4165,
    },
    {
        "id": 7,
        "name": "EpicLAN Center",
        "city": "Наманган",
        "address": "ул. Достлик 8",
        "latitude": 40.9983,
        "longitude": 71.6726,
    },
]

async def update_clubs():
    async with async_session_factory() as session:
        for data in DEMO_CLUBS:
            club = await session.get(Club, data["id"])
            if club:
                club.name = data["name"]
                club.city = data["city"]
                club.address = data["address"]
                club.latitude = data["latitude"]
                club.longitude = data["longitude"]
                print(f"  Updated Club {club.id}: {club.name} ({club.city})")
            else:
                print(f"  Club {data['id']} not found, skipping.")
        
        await session.commit()
        print("Done! All clubs updated.")

if __name__ == "__main__":
    asyncio.run(update_clubs())
