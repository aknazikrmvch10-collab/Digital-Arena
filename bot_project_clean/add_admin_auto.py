"""Auto-add first admin with ID 1083902919"""
import asyncio
from sqlalchemy import select
from database import init_db, async_session_factory
from models import Admin

async def add_admin():
    await init_db()
    
    admin_tg_id = 1083902919
    
    async with async_session_factory() as session:
        result = await session.execute(select(Admin).where(Admin.tg_id == admin_tg_id))
        existing = result.scalars().first()
        
        if existing:
            print(f"Admin {admin_tg_id} already exists")
        else:
            new_admin = Admin(tg_id=admin_tg_id)
            session.add(new_admin)
            await session.commit()
            print(f"Super admin {admin_tg_id} added successfully!")

if __name__ == "__main__":
    asyncio.run(add_admin())
