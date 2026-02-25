import asyncio
from sqlalchemy import text
from database import engine

async def migrate():
    print("Starting migration: Ensuring phone column exists in users table...")
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TABLE users ADD COLUMN phone VARCHAR"))
            print("Successfully added 'phone' column to users table.")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                print("Column 'phone' already exists in users table.")
            else:
                print(f"Migration failed: {e}")

if __name__ == "__main__":
    asyncio.run(migrate())
