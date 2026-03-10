"""
database/engine.py — Async SQLAlchemy engine setup.

Uses asyncpg driver for PostgreSQL.
Session factory is used by services via dependency injection.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import config
from database.models.base import Base

# Create async engine — pool_pre_ping keeps connections healthy
engine = create_async_engine(
    config.database_url,
    echo=False,          # Set True to log SQL during development
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Session factory — used to create sessions in services
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Context manager that yields a database session and handles cleanup."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Create all tables if they don't exist. Called on bot startup."""
    # Import all models so SQLAlchemy registers them before create_all
    import database.models.user         # noqa
    import database.models.category     # noqa
    import database.models.transaction  # noqa

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
