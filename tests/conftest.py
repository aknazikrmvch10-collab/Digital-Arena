"""
Test fixtures for Digital Arena.
Uses in-memory SQLite for fast, isolated tests.
"""
import asyncio
import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Force test environment BEFORE any app imports
os.environ["BOT_TOKEN"] = "0000000000:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
os.environ["DB_URL"] = "sqlite+aiosqlite:///file:testdb?mode=memory&cache=shared&uri=true"
os.environ["ADMIN_IDS"] = "123456"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["ALLOWED_ORIGINS"] = "http://localhost:3000"

from database import Base
import database as db_module


@pytest_asyncio.fixture
async def db_session():
    """Create and wipe in-memory SQLite database for each test."""
    # Use init_db to create tables AND run all ALTER TABLE column migrations
    await db_module.init_db()

    # Yield a session for the test
    async with db_module.async_session_factory() as session:
        yield session

    # Teardown: drop tables so the next test is fully isolated
    async with db_module.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(db_session):
    """FastAPI test client using the test database."""
    from main import fastapi_app
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
