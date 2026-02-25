import asyncio
import logging
from database import async_session_factory, init_db
from models import Club, Computer

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_demo_club():
    await init_db()
    
    async with async_session_factory() as session:
        # 1. Создаем или обновляем главный демо-клуб
        logger.info("Создаем клуб 'CyberArena Pro'...")
        
        # Проверяем, есть ли уже клубы, если да - удаляем все старые компьютеры для чистоты
        # (в реальной жизни так не делать, но для настройки демо - ок)
        # Но лучше просто создадим новый или обновим существующий ID=1
        
        club = await session.get(Club, 1)
        if not club:
            club = Club(id=1)
            session.add(club)
        
        club.name = "CyberArena Pro"
        club.city = "Tashkent"
        club.address = "Mirabad District, Oybek 12"
        club.latitude = 41.2995
        club.longitude = 69.2401
        club.driver_type = "MOCK" # Для демо идеально
        club.connection_config = {"club_id": 1}
        club.admin_phone = "+998 50 747 49 34"
        club.working_hours = "24/7"
        
        # Удаляем старые компьютеры этого клуба, чтобы не дублировать
        # Примечание: Это грубая очистка для скрипта
        from sqlalchemy import delete
        await session.execute(delete(Computer).where(Computer.club_id == 1))
        
        computers = []
        
        # --- 1. ОБЩИЙ ЗАЛ (General) ---
        # 20 компьютеров: 1-10 и 11-20
        logger.info("Добавляем Общий зал (20 ПК)...")
        for i in range(1, 21):
            computers.append(Computer(
                club_id=1,
                name=f"General-{i}",
                zone="General",
                cpu="Intel Core i5-12400F",
                gpu="RTX 3060 12GB",
                ram_gb=16,
                monitor_hz=165,
                price_per_hour=10000,
                is_active=True
            ))

        # --- 2. СТАНДАРТ (Standard) ---
        # 2 комнаты по 10 ПК (всего 20)
        # Комната 1 (CS:GO Room)
        logger.info("Добавляем Room 1 (CS:GO)...")
        for i in range(1, 11):
            computers.append(Computer(
                club_id=1,
                name=f"CSGO-{i}",
                zone="Standard Room 1",
                cpu="Intel Core i5-13400",
                gpu="RTX 4060",
                ram_gb=16,
                monitor_hz=240,
                price_per_hour=15000,
                is_active=True
            ))
            
        # Комната 2 (Dota Room)
        logger.info("Добавляем Room 2 (Standard)...")
        for i in range(1, 11):
            computers.append(Computer(
                club_id=1,
                name=f"Stand-{i}",
                zone="Standard Room 2",
                cpu="Intel Core i5-13400",
                gpu="RTX 4060",
                ram_gb=16,
                monitor_hz=240,
                price_per_hour=15000,
                is_active=True
            ))

        # --- 3. ПРЕМИУМ (Premium) ---
        # 2 комнаты по 10 ПК
        # Premium A
        logger.info("Добавляем Premium A...")
        for i in range(1, 11):
            computers.append(Computer(
                club_id=1,
                name=f"Prem-A{i}",
                zone="Premium Room A",
                cpu="Intel Core i7-13700K",
                gpu="RTX 4070 Ti",
                ram_gb=32,
                monitor_hz=360,
                price_per_hour=25000,
                is_active=True
            ))
            
        # Premium B
        logger.info("Добавляем Premium B...")
        for i in range(1, 11):
            computers.append(Computer(
                club_id=1,
                name=f"Prem-B{i}",
                zone="Premium Room B",
                cpu="Intel Core i7-13700K",
                gpu="RTX 4070 Ti",
                ram_gb=32,
                monitor_hz=360,
                price_per_hour=25000,
                is_active=True
            ))

        # --- 4. VIP КОМНАТЫ (Ultra) ---
        # 3 комнаты по 5 ПК
        zones = ["VIP Alpha", "VIP Beta", "VIP Omega"]
        for idx, zone_name in enumerate(zones):
            logger.info(f"Добавляем {zone_name}...")
            for i in range(1, 6):
                computers.append(Computer(
                    club_id=1,
                    name=f"VIP-{idx+1}-{i}",
                    zone=zone_name,
                    cpu="Intel Core i9-13900K",
                    gpu="RTX 4090",
                    ram_gb=64,
                    monitor_hz=540, # Ultra fast
                    price_per_hour=50000,
                    is_active=True
                ))

        session.add_all(computers)
        await session.commit()
        
        logger.info("Клуб настроен на 100% для показа инвестору.")

if __name__ == "__main__":
    asyncio.run(create_demo_club())
