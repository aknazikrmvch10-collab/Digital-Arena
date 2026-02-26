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
        
    # Safe auto-migration for missing column
    # Must be done in separate transactions so a failure doesn't abort the entire startup
    from sqlalchemy import text
    try:
        # Try PostgreSQL syntax
        async with engine.begin() as conn:
            await conn.execute(text("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS confirmation_code VARCHAR"))
    except Exception:
        # Try SQLite fallback
        try:
            async with engine.begin() as conn:
                await conn.execute(text("ALTER TABLE bookings ADD COLUMN confirmation_code VARCHAR"))
        except Exception:
            pass  # Ignore if it already exists or fails
