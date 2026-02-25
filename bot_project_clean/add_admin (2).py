import asyncio
from sqlalchemy import select
from database import async_session_factory
from models import Admin

async def add_admin(tg_id: int):
    async with async_session_factory() as session:
        result = await session.execute(select(Admin).where(Admin.tg_id == tg_id))
        if result.scalars().first():
            print(f'Admin with ID {tg_id} already exists')
            return
        admin = Admin(tg_id=tg_id)
        session.add(admin)
        await session.commit()
        print(f'Admin with ID {tg_id} added')

if __name__ == '__main__':
    tg_id = 1450190990
    asyncio.run(add_admin(tg_id))
