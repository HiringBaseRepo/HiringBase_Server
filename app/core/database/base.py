"""SQLAlchemy async database setup."""
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

from app.core.config import settings

# Determine if we are in testing environment
IS_TESTING = settings.APP_ENV == "testing"

def create_engine_instance():
    # Engine configuration
    engine_kwargs = {
        "echo": settings.DEBUG,
        "future": True,
    }

    if IS_TESTING:
        # Use NullPool for testing to avoid connection reuse/leak issues
        engine_kwargs["poolclass"] = NullPool
    else:
        # Standard pooling for development/production
        engine_kwargs["pool_size"] = 10
        engine_kwargs["max_overflow"] = 20

    return create_async_engine(
        str(settings.DATABASE_URL),
        **engine_kwargs
    )

engine = create_engine_instance()

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

Base = declarative_base()


async def get_db() -> AsyncSession:
    """Dependency to get async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
