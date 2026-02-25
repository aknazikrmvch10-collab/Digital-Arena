import asyncio
from sqlalchemy import text
from database import engine

async def migrate():
    print("Starting migration: Adding item_id to bookings table...")
    async with engine.begin() as conn:
        try:
            # Check if column exists first? 
            # SQLite doesn't support IF NOT EXISTS for columns easily in one statement usually, 
            # but we can just try to add it.
            await conn.execute(text("ALTER TABLE bookings ADD COLUMN item_id INTEGER"))
            print("Successfully added 'item_id' column.")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                print("Column 'item_id' already exists.")
            else:
                print(f"Migration failed: {e}")

if __name__ == "__main__":
    asyncio.run(migrate())
