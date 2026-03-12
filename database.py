from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from config import settings

engine_kwargs = {"echo": False}
if ":memory:" in settings.async_db_url:
    from sqlalchemy.pool import StaticPool
    engine_kwargs.update({
        "poolclass": StaticPool,
        "connect_args": {"check_same_thread": False}
    })

engine = create_async_engine(settings.async_db_url, **engine_kwargs)

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
        # Wave 3: User language preference
        ("ALTER TABLE users ADD COLUMN IF NOT EXISTS language VARCHAR DEFAULT 'ru'",
         "ALTER TABLE users ADD COLUMN language VARCHAR DEFAULT 'ru'"),
        # Wave 4: Payments table
        ("""CREATE TABLE IF NOT EXISTS payments (
            id SERIAL PRIMARY KEY,
            booking_id INTEGER NOT NULL REFERENCES bookings(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            amount INTEGER NOT NULL,
            currency VARCHAR DEFAULT 'UZS',
            provider VARCHAR DEFAULT 'test' NOT NULL,
            transaction_id VARCHAR,
            status VARCHAR DEFAULT 'pending' NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            paid_at TIMESTAMP WITH TIME ZONE
        )""",
         """CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER NOT NULL REFERENCES bookings(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            amount INTEGER NOT NULL,
            currency VARCHAR DEFAULT 'UZS',
            provider VARCHAR DEFAULT 'test' NOT NULL,
            transaction_id VARCHAR,
            status VARCHAR DEFAULT 'pending' NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            paid_at TIMESTAMP
        )"""),
        # Wave 6: Password-based auth (multi-device login)
        ("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR",
         "ALTER TABLE users ADD COLUMN password_hash VARCHAR"),
        # Wave 7: Bookings pricing
        ("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS total_price INTEGER DEFAULT 0",
         "ALTER TABLE bookings ADD COLUMN total_price INTEGER DEFAULT 0"),
        ("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS discount_amount INTEGER DEFAULT 0",
         "ALTER TABLE bookings ADD COLUMN discount_amount INTEGER DEFAULT 0"),
        ("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS earned_points INTEGER DEFAULT 0",
         "ALTER TABLE bookings ADD COLUMN earned_points INTEGER DEFAULT 0"),
        # Wave 8: Loyalty and Bar
        ("ALTER TABLE users ADD COLUMN IF NOT EXISTS loyalty_level VARCHAR DEFAULT 'Начинающий'",
         "ALTER TABLE users ADD COLUMN loyalty_level VARCHAR DEFAULT 'Начинающий'"),
        ("ALTER TABLE users ADD COLUMN IF NOT EXISTS bonus_points INTEGER DEFAULT 0",
         "ALTER TABLE users ADD COLUMN bonus_points INTEGER DEFAULT 0"),
        ("ALTER TABLE users ADD COLUMN IF NOT EXISTS balance INTEGER DEFAULT 0",
         "ALTER TABLE users ADD COLUMN balance INTEGER DEFAULT 0"),
    ]

    # Wave 5: Seed default Tashkent coordinates for clubs that have none
    # Uses Python loop so it works on both PostgreSQL and SQLite.
    try:
        async with async_session_factory() as session:
            from sqlalchemy import text as _text
            result = await session.execute(
                _text("SELECT id FROM clubs WHERE latitude IS NULL OR longitude IS NULL ORDER BY id")
            )
            club_ids = [row[0] for row in result.fetchall()]
            for idx, club_id in enumerate(club_ids):
                # Tashkent center ~41.2995, 69.2401 — offset ~100m per club
                lat = 41.2995 + idx * 0.0009
                lng = 69.2401 + idx * 0.0009
                await session.execute(
                    _text("UPDATE clubs SET latitude = :lat, longitude = :lng WHERE id = :id"),
                    {"lat": lat, "lng": lng, "id": club_id}
                )
            await session.commit()
    except Exception:
        pass  # Table might not exist yet on first run
    
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
