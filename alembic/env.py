"""
alembic/env.py
==============
Alembic migration environment.
Reads DB connection URL from the app's config (which in turn reads from .env or
environment variables set by Render/Docker).

Works with both SQLite (local dev) and PostgreSQL (production).
"""
import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

# ── Alembic config object ────────────────────────────────────────────────────
config = context.config

# Set up loggers from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Import ALL models so Alembic can autogenerate migrations ─────────────────
from database import Base
from models import (
    User, Club, Computer, Booking, Admin,
    RestaurantTable, ClubZoneSetting, AuditLog,
    Review, PromoCode, AppAuthCode, AppSession,
    Payment, BarItem, BarOrder,
    IcafeSession, AuditDiscrepancy,
)

target_metadata = Base.metadata


# ── Read DB URL from environment (same as the app does) ──────────────────────
def get_url() -> str:
    """
    Priority:
    1. DATABASE_URL env var (set automatically by Render PostgreSQL addon)
    2. DB_URL env var (our custom var set in render.yaml / .env)
    3. Fallback to alembic.ini [sqlalchemy.url]
    """
    from config import settings
    url = settings.async_db_url
    # Alembic needs the sync URL for certain operations — but since we use
    # async_engine_from_config we keep the async+asyncpg URL.
    return url


# ── Offline mode (generate SQL without connecting) ───────────────────────────
def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Compare server defaults so Alembic detects DEFAULT value changes
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online mode (connect and migrate) ────────────────────────────────────────
def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_server_default=True,
        # For PostgreSQL: include schemas
        include_schemas=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    url = get_url()

    # Override the sqlalchemy.url from alembic.ini with our dynamic URL
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = url

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # NullPool: don't keep connections open during migrations
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


# ── Entry point ───────────────────────────────────────────────────────────────
if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
