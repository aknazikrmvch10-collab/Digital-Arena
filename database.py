"""
database.py
============
Database engine configuration.

Supports two modes automatically based on DB_URL:
  - SQLite   → local development (DB_URL=sqlite+aiosqlite:///./digital_arena.db)
  - PostgreSQL → production on Render (DB_URL=postgresql://... or postgres://...)

On PostgreSQL, uses a proper connection pool (min 2, max 10 connections).
On SQLite, uses StaticPool (single connection, safe for :memory: test mode).
"""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from config import settings

# ── Pick the right engine kwargs based on database dialect ──────────────────
_url = settings.async_db_url
_is_sqlite = "sqlite" in _url
_is_postgres = "postgresql" in _url or "asyncpg" in _url

if ":memory:" in _url:
    # In-memory SQLite — used in tests, requires a single shared connection
    from sqlalchemy.pool import StaticPool
    engine = create_async_engine(
        _url,
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
elif _is_sqlite:
    # File-based SQLite — local development
    engine = create_async_engine(
        _url,
        echo=False,
        connect_args={"check_same_thread": False},
    )
else:
    # PostgreSQL — production (Render, etc.)
    # pool_pre_ping: automatically reconnects on dropped connections
    # pool_size + max_overflow: handles concurrent async requests safely
    engine = create_async_engine(
        _url,
        echo=False,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,  # Recycle connections every 30 minutes
    )

async_session_factory = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session_factory() as session:
        yield session


async def init_db():
    """
    Initialize database on startup.

    On PostgreSQL: Alembic handles all schema migrations via `start.sh`.
                   We only create tables that are MISSING (safety net).
    On SQLite:     We run the full manual migration list as a fallback.
    """
    from sqlalchemy import text

    # Always try to create any missing tables via SQLAlchemy metadata
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # ── Seed Tashkent coords for clubs without geo data ──────────────────────
    try:
        async with async_session_factory() as session:
            result = await session.execute(
                text("SELECT id FROM clubs WHERE latitude IS NULL OR longitude IS NULL ORDER BY id")
            )
            club_ids = [row[0] for row in result.fetchall()]
            for idx, club_id in enumerate(club_ids):
                lat = 41.2995 + idx * 0.0009
                lng = 69.2401 + idx * 0.0009
                await session.execute(
                    text("UPDATE clubs SET latitude = :lat, longitude = :lng WHERE id = :id"),
                    {"lat": lat, "lng": lng, "id": club_id},
                )
            await session.commit()
    except Exception:
        pass  # Table might not exist on very first run

    # ── SQLite-only fallback migrations (not needed on PostgreSQL/Alembic) ───
    if not _is_sqlite:
        return  # PostgreSQL: Alembic already ran all migrations in start.sh

    migrations_sqlite = [
        "ALTER TABLE bookings ADD COLUMN confirmation_code VARCHAR",
        "ALTER TABLE users ADD COLUMN referral_code VARCHAR",
        "ALTER TABLE users ADD COLUMN referred_by INTEGER",
        "ALTER TABLE users ADD COLUMN referral_bonus_used BOOLEAN DEFAULT FALSE",
        "ALTER TABLE clubs ADD COLUMN description VARCHAR",
        "ALTER TABLE clubs ADD COLUMN image_url VARCHAR",
        "ALTER TABLE clubs ADD COLUMN wifi_speed VARCHAR",
        "ALTER TABLE clubs ADD COLUMN club_admin_tg_ids VARCHAR",
        "ALTER TABLE admins ADD COLUMN club_id INTEGER",
        "ALTER TABLE users ADD COLUMN language VARCHAR DEFAULT 'ru'",
        "ALTER TABLE users ADD COLUMN password_hash VARCHAR",
        "ALTER TABLE bookings ADD COLUMN total_price INTEGER DEFAULT 0",
        "ALTER TABLE bookings ADD COLUMN discount_amount INTEGER DEFAULT 0",
        "ALTER TABLE bookings ADD COLUMN earned_points INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN loyalty_level VARCHAR DEFAULT 'Начинающий'",
        "ALTER TABLE users ADD COLUMN bonus_points INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN balance INTEGER DEFAULT 0",
    ]

    for sql in migrations_sqlite:
        try:
            async with engine.begin() as conn:
                await conn.execute(text(sql))
        except Exception:
            pass  # Column already exists — safe to ignore on SQLite
