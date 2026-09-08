"""Database engine and session lifecycle."""

from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

database_url = get_settings().database_url

engine = create_async_engine(database_url, pool_pre_ping=True)
AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Yield one request-scoped database session."""

    async with AsyncSessionFactory() as session:
        yield session


async def check_database_connection() -> bool:
    """Return whether PostgreSQL accepts a trivial query."""

    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception:  # The readiness endpoint reports failure without leaking details.
        return False
    return True


async def dispose_database_engine() -> None:
    """Close pooled database connections during application shutdown."""

    await engine.dispose()
