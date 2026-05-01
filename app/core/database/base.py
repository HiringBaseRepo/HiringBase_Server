"""SQLAlchemy async database setup."""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

from app.core.config import settings

engine = create_async_engine(
    str(settings.DATABASE_URL),
    echo=settings.DEBUG,
    future=True,
    pool_size=10,
    max_overflow=20,
)

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
