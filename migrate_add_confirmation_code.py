import asyncio
from sqlalchemy import text
from database import engine

async def migrate():
    print("Starting migration: Adding confirmation_code to bookings table...")
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TABLE bookings ADD COLUMN confirmation_code VARCHAR"))
            print("Successfully added 'confirmation_code' column.")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("Column 'confirmation_code' already exists.")
            else:
                print(f"Migration failed: {e}")

if __name__ == "__main__":
    asyncio.run(migrate())
