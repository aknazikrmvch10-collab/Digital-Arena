import asyncio
from database import init_db
from models import AuditLog

async def main():
    print("Creating tables...")
    await init_db()
    print("Tables created successfully (including AuditLog if missing).")

if __name__ == "__main__":
    asyncio.run(main())
