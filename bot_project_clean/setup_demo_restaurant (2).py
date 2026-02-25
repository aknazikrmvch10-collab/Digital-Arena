import asyncio
import logging
from database import async_session_factory, init_db
from models import Club, RestaurantTable, Computer
from sqlalchemy import delete

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_demo_restaurant():
    await init_db()
    
    async with async_session_factory() as session:
        logger.info("Создаем ресторан 'CyberFood & Lounge'...")
        
        # 1. Создаем или обновляем клуб (ресторан)
        # Используем ID=2 для разделения с комп. клубом
        club = await session.get(Club, 2)
        if not club:
            club = Club(id=2)
            session.add(club)
        
        club.name = "CyberFood & Lounge"
        club.city = "Tashkent"
        club.address = "Amir Temur Ave, 107"
        club.latitude = 41.3333
        club.longitude = 69.2833
        club.venue_type = "restaurant" # КРИТИЧНО для переключения UI
        club.driver_type = "MOCK"
        club.connection_config = {"club_id": 2}
        
        # Очищаем старые данные
        await session.execute(delete(RestaurantTable).where(RestaurantTable.club_id == 2))
        
        tables = []
        
        # --- 1. ОБЩИЙ ЗАЛ (Main Hall) ---
        logger.info("Добавляем столы в Общий зал...")
        for i in range(1, 11):
            tables.append(RestaurantTable(
                club_id=2,
                name=f"Стол {i}",
                zone="Основной зал",
                seats=4,
                position="Центр",
                min_deposit=200000,
                booking_price=0,
                image_url="https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?auto=format&fit=crop&w=800&q=80",
                is_active=True
            ))

        # --- 2. ТЕРРАСА (Terrace) ---
        logger.info("Добавляем столы на Террасу...")
        for i in range(1, 6):
            tables.append(RestaurantTable(
                club_id=2,
                name=f"Терраса {i}",
                zone="Летняя терраса",
                seats=2,
                position="Окно",
                min_deposit=150000,
                booking_price=0,
                image_url="https://images.unsplash.com/photo-1515003197210-e0cd71810b5f?auto=format&fit=crop&w=800&q=80",
                is_active=True
            ))

        # --- 3. VIP КАБИНКИ ---
        logger.info("Добавляем VIP кабинки...")
        for i in range(1, 4):
            tables.append(RestaurantTable(
                club_id=2,
                name=f"VIP Lounge {i}",
                zone="VIP Зона",
                seats=8,
                position="Приватная зона",
                min_deposit=1000000,
                booking_price=50000, # Платная бронь для VIP
                image_url="https://images.unsplash.com/photo-1574096079513-d8259312b785?auto=format&fit=crop&w=800&q=80",
                is_active=True
            ))

        session.add_all(tables)
        await session.commit()
        
        logger.info(f"✅ Успешно добавлено {len(tables)} столов в базу!")
        logger.info("Ресторан настроен. URL для тестирования: ?club_id=2")

if __name__ == "__main__":
    asyncio.run(create_demo_restaurant())
