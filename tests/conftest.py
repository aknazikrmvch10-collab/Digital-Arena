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
os.environ["DB_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["ADMIN_IDS"] = "123456"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["ALLOWED_ORIGINS"] = "http://localhost:3000"

from database import Base
import database as db_module


@pytest_asyncio.fixture
async def db_session():
    """Create an in-memory SQLite database for each test."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    # Monkey-patch the global session factory so the app uses our test DB
    original_factory = db_module.async_session_factory
    db_module.async_session_factory = session_factory

    async with session_factory() as session:
        yield session

    db_module.async_session_factory = original_factory
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    """FastAPI test client using the test database."""
    from main import fastapi_app
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
