"""
Database connection and session management.

SQLAlchemy 2.0 with async support via asyncpg.

Session lifecycle:
- A new database session is created for each HTTP request
- The session is committed if the request succeeds
- The session is rolled back if an exception occurs
- The session is always closed after the request (connection returned to pool)

This is handled by the get_db() dependency injected into route handlers.
"""

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from core.config import settings

# Convert standard PostgreSQL URL to async version
# postgresql:// → postgresql+asyncpg://
ASYNC_DATABASE_URL = settings.DATABASE_URL.replace(
    "postgresql://", "postgresql+asyncpg://"
)

# Create the async engine
# pool_pre_ping=True: test connections before using them (handles dropped connections)
engine = create_async_engine(
    ASYNC_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,       # Max connections in the pool
    max_overflow=20,    # Extra connections allowed beyond pool_size
    echo=settings.ENVIRONMENT == "development",  # Log SQL in dev only
)

# Session factory — creates new AsyncSession instances
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Don't expire objects after commit (avoids lazy load issues)
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


async def get_db() -> AsyncSession:
    """
    FastAPI dependency that provides a database session per request.

    Usage in a route:
        @router.get("/")
        async def my_route(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
