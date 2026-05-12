import redis.asyncio as redis
from typing import Optional
from app.core.config import settings
import structlog

logger = structlog.get_logger(__name__)

class RedisClient:
    def __init__(self):
        self.redis: Optional[redis.Redis] = None

    async def connect(self):
        if not settings.REDIS_URL:
            logger.warning("REDIS_URL not set, caching disabled")
            return
        
        try:
            self.redis = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=5.0,
            )
            await self.redis.ping()
            logger.info("Connected to Redis successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis = None

    async def disconnect(self):
        if self.redis:
            await self.redis.close()
            logger.info("Disconnected from Redis")

redis_client = RedisClient()
