import asyncio
from database import init_db, async_session_factory
from models import Admin
from sqlalchemy import select

async def check():
    await init_db()
    async with async_session_factory() as s:
        r = await s.execute(select(Admin))
        admins = r.scalars().all()
        print('Admins in DB:', [a.tg_id for a in admins])

asyncio.run(check())
