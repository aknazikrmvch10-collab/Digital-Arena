import asyncio
from database import engine, Base
from models import *

async def drop_all():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        print("Dropped all tables.")

if __name__ == "__main__":
    asyncio.run(drop_all())
