from typing import Optional, AsyncGenerator
import structlog
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings

logger = structlog.get_logger()

_mongo_client: Optional[AsyncIOMotorClient] = None
_DB_NAME = "hiringbase_bigdata"

async def connect_mongo() -> Optional[AsyncIOMotorClient]:
    """
    Initializes the MongoDB client at application startup.
    """
    global _mongo_client
    if not settings.MONGODB_URL:
        logger.warn("mongodb_url_missing", message="MongoDB integration is not configured. Features depending on MongoDB will be disabled.")
        return None
        
    try:
        # Pinned configuration for reliability and pooling
        _mongo_client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            maxPoolSize=50
        )
        # Verify connection by triggering a quick select
        await _mongo_client.admin.command('ping')
        logger.info("mongodb_connection_established")
        return _mongo_client
    except Exception as e:
        logger.error("mongodb_connection_failed", error=str(e))
        _mongo_client = None
        return None

async def disconnect_mongo():
    """
    Closes the MongoDB client connection at application shutdown.
    """
    global _mongo_client
    if _mongo_client is not None:
        _mongo_client.close()
        _mongo_client = None
        logger.info("mongodb_connection_closed")

async def get_mongo_db() -> AsyncGenerator[Optional[AsyncIOMotorClient], None]:
    """
    Dependency injection for FastAPI endpoints.
    Yields the motor database instance if client is configured, otherwise None.
    """
    global _mongo_client
    if _mongo_client is None:
        yield None
    else:
        yield _mongo_client[_DB_NAME]
