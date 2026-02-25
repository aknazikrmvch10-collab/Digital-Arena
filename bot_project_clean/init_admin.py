"""
Script to initialize the first super admin in the database.
Run this once before starting the bot for the first time.
"""
import asyncio
from sqlalchemy import select
from database import init_db, async_session_factory
from models import Admin

async def add_first_admin():
    """Add the first super admin to the database."""
    # Initialize database (creates tables if they don't exist)
    await init_db()
    
    print("=== Инициализация первого супер-администратора ===\n")
    
    # Ask for Telegram ID
    try:
        admin_tg_id = int(input("Введите ваш Telegram ID (можно узнать у @userinfobot): "))
    except ValueError:
        print("❌ Ошибка: введите число (ваш Telegram ID)")
        return
    
    # Check if admin already exists
    async with async_session_factory() as session:
        result = await session.execute(select(Admin).where(Admin.tg_id == admin_tg_id))
        existing_admin = result.scalars().first()
        
        if existing_admin:
            print(f"ℹ️ Администратор с ID {admin_tg_id} уже существует в базе.")
            return
        
        # Add new admin
        new_admin = Admin(tg_id=admin_tg_id)
        session.add(new_admin)
        await session.commit()
        
        print(f"✅ Супер-администратор с ID {admin_tg_id} успешно добавлен!")
        print(f"\nТеперь вы можете запустить бота командой: python main.py")
        print(f"После запуска используйте команду /admin в Telegram для доступа к админ-панели.")

if __name__ == "__main__":
    asyncio.run(add_first_admin())
