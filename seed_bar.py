import asyncio
from database import async_session_factory
from models import BarItem

async def seed_bar_items():
    async with async_session_factory() as session:
        async with session.begin():
            items = [
                BarItem(name="Кола (0.5л)", category="Напитки", price=12000, image_url="https://images.unsplash.com/photo-1622483767028-3f66f32aef97?w=300&q=80"),
                BarItem(name="Энергетик RedBull", category="Напитки", price=25000, image_url="https://images.unsplash.com/photo-1625772299848-391b6a510d41?w=300&q=80"),
                BarItem(name="Чипсы Lays (Сыр)", category="Снеки", price=15000, image_url="https://images.unsplash.com/photo-1566478989037-eade3f79029a?w=300&q=80"),
                BarItem(name="Сэндвич с курицей", category="Еда", price=28000, image_url="https://images.unsplash.com/photo-1528735602780-2552fd46c7af?w=300&q=80"),
            ]
            session.add_all(items)
    print("✅ Добавлены демо-товары в бар!")

if __name__ == "__main__":
    asyncio.run(seed_bar_items())
