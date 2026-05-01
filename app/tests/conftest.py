"""Pytest fixtures."""
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.base import AsyncSessionLocal


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    session = AsyncSessionLocal()
    try:
        yield session
    finally:
        await session.rollback()
        await session.close()
