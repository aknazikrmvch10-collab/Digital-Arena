import asyncio
from database import engine
from sqlalchemy import text

async def migrate():
    async with engine.begin() as conn:
        # 1. Add venue_type column to clubs if it doesn't exist
        print("Checking clubs table...")
        try:
            # SQLite specific check
            await conn.execute(text("ALTER TABLE clubs ADD COLUMN venue_type VARCHAR DEFAULT 'computer_club'"))
            print("Added venue_type column to clubs")
        except Exception as e:
            if "duplicate column name" in str(e):
                print("Column venue_type already exists")
            else:
                print(f"Note: {e}")

        # 2. Create restaurant_tables table
        print("Creating restaurant_tables table...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS restaurant_tables (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                club_id INTEGER REFERENCES clubs(id),
                name VARCHAR,
                zone VARCHAR,
                seats INTEGER DEFAULT 4,
                position VARCHAR,
                min_deposit INTEGER DEFAULT 0,
                booking_price INTEGER DEFAULT 0,
                image_url VARCHAR,
                is_active BOOLEAN DEFAULT TRUE
            )
        """))
        
        # Create index manually as it is not created by CREATE TABLE in sqlite with alchemy shorthand in this raw query
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_restaurant_tables_club_id ON restaurant_tables (club_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_restaurant_tables_id ON restaurant_tables (id)"))

        print("Migration complete!")

if __name__ == "__main__":
    asyncio.run(migrate())
