"""
Quick script to add a super-admin to the database.
Run locally with: python setup_admin.py <YOUR_TELEGRAM_ID>

To find your Telegram ID:
  1. Write to @userinfobot in Telegram
  2. It will reply with your numeric ID (e.g. 123456789)

Usage:
  python setup_admin.py 123456789
"""
import asyncio
import sys
from database import async_session_factory, init_db
from models import Admin
from sqlalchemy import select


async def add_admin(tg_id: int, club_id: int = None):
    await init_db()
    async with async_session_factory() as session:
        # Check if already exists
        result = await session.execute(select(Admin).where(Admin.tg_id == tg_id))
        existing = result.scalars().first()

        if existing:
            print(f"⚠️  Admin с TG ID {tg_id} уже существует.")
            if club_id is not None:
                existing.club_id = club_id
                await session.commit()
                print(f"✅ club_id обновлён → {club_id}")
            else:
                print("ℹ️  Это суперадмин (доступ ко всем клубам).")
            return

        async with session.begin():
            admin = Admin(
                tg_id=tg_id,
                club_id=club_id  # None = super-admin (all clubs)
            )
            session.add(admin)

    role = "Суперадмин" if club_id is None else f"Клубный админ (club_id={club_id})"
    print(f"✅ Добавлен администратор!")
    print(f"   TG ID : {tg_id}")
    print(f"   Роль  : {role}")
    print(f"\nТеперь напиши боту /admin 🎉")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python setup_admin.py <TELEGRAM_ID> [club_id]")
        print("Пример:        python setup_admin.py 123456789")
        print("               python setup_admin.py 123456789 1   (админ клуба #1)")
        sys.exit(1)

    tg_id_arg = int(sys.argv[1])
    club_id_arg = int(sys.argv[2]) if len(sys.argv) > 2 else None
    asyncio.run(add_admin(tg_id_arg, club_id_arg))
