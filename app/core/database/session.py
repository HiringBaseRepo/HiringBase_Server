"""Database session utilities."""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.base import AsyncSessionLocal


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Standalone async session context manager for background tasks."""
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
