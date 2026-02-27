from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from config import settings

engine = create_async_engine(settings.async_db_url, echo=False)

async_session_factory = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncSession:
    async with async_session_factory() as session:
        yield session

async def init_db():
    # First, configure the base tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    # Safe auto-migration for all columns
    # Each ALTER TABLE is in its own transaction so one failure doesn't abort the rest
    from sqlalchemy import text
    migrations = [
        # Confirmation code (Wave 1)
        ("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS confirmation_code VARCHAR",
         "ALTER TABLE bookings ADD COLUMN confirmation_code VARCHAR"),
        # Wave 2: User referral fields
        ("ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_code VARCHAR UNIQUE",
         "ALTER TABLE users ADD COLUMN referral_code VARCHAR"),
        ("ALTER TABLE users ADD COLUMN IF NOT EXISTS referred_by INTEGER",
         "ALTER TABLE users ADD COLUMN referred_by INTEGER"),
        ("ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_bonus_used BOOLEAN DEFAULT FALSE",
         "ALTER TABLE users ADD COLUMN referral_bonus_used BOOLEAN DEFAULT FALSE"),
        # Wave 2: Club settings
        ("ALTER TABLE clubs ADD COLUMN IF NOT EXISTS description VARCHAR",
         "ALTER TABLE clubs ADD COLUMN description VARCHAR"),
        ("ALTER TABLE clubs ADD COLUMN IF NOT EXISTS image_url VARCHAR",
         "ALTER TABLE clubs ADD COLUMN image_url VARCHAR"),
        ("ALTER TABLE clubs ADD COLUMN IF NOT EXISTS wifi_speed VARCHAR",
         "ALTER TABLE clubs ADD COLUMN wifi_speed VARCHAR"),
        ("ALTER TABLE clubs ADD COLUMN IF NOT EXISTS club_admin_tg_ids VARCHAR",
         "ALTER TABLE clubs ADD COLUMN club_admin_tg_ids VARCHAR"),
        # Wave 2: Admin club_id
        ("ALTER TABLE admins ADD COLUMN IF NOT EXISTS club_id INTEGER",
         "ALTER TABLE admins ADD COLUMN club_id INTEGER"),
    ]
    
    for pg_sql, sqlite_sql in migrations:
        try:
            async with engine.begin() as conn:
                await conn.execute(text(pg_sql))
        except Exception:
            try:
                async with engine.begin() as conn:
                    await conn.execute(text(sqlite_sql))
            except Exception:
                pass  # Column already exists or not applicable
