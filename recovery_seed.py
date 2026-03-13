import asyncio
import os
import sys
from database import init_db, async_session_factory
from seed_data import seed_test_clubs
from seed_bar import seed_bar_items
from sqlalchemy import text

async def main():
    print("--- Starting recovery of baseline data on PostgreSQL ---")
    
    # Ensure tables are created
    await init_db()
    
    async with async_session_factory() as session:
        # 1. Seed main Clubs and Computers
        print("[*] Seeding default clubs and PCs...")
        await seed_test_clubs()
        
        # 2. Seed Bar items
        print("[*] Seeding bar menu items...")
        await seed_bar_items()
        
        # 3. Add SuperAdmin
        admin_ids = os.getenv("ADMIN_IDS", "123456789").split(",")
        for admin_id in admin_ids:
            if admin_id.strip():
                try:
                    tg_id = int(admin_id.strip())
                    # Check if exists
                    res = await session.execute(text("SELECT id FROM admins WHERE tg_id = :tid"), {"tid": tg_id})
                    if not res.fetchone():
                        # Based on models.py: Admin has id, tg_id, club_id (None for super), created_at
                        await session.execute(text("INSERT INTO admins (tg_id, club_id) VALUES (:tid, NULL)"), {"tid": tg_id})
                        print(f"[OK] Added super-admin: {tg_id}")
                except Exception as e:
                    print(f"[!] Skip admin {admin_id}: {e}")
                    continue
        
        await session.commit()
    
    print("--- Recovery Complete ---")

if __name__ == "__main__":
    asyncio.run(main())
