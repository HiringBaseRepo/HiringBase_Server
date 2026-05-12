import json
import hashlib
from typing import Any, Optional
from app.core.cache.client import redis_client
import structlog

logger = structlog.get_logger(__name__)

class RedisCacheService:
    @staticmethod
    def _generate_key(prefix: str, identifier: str) -> str:
        # Use MD5 hash for identifier to keep keys short (useful for 256MB limit)
        hashed_id = hashlib.md5(identifier.encode()).hexdigest()
        return f"cache:{prefix}:{hashed_id}"

    async def get(self, prefix: str, identifier: str) -> Optional[Any]:
        if not redis_client.redis:
            return None
        
        key = self._generate_key(prefix, identifier)
        try:
            data = await redis_client.redis.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
        
        return None

    async def set(self, prefix: str, identifier: str, value: Any, expire: int = 3600):
        if not redis_client.redis:
            return
        
        key = self._generate_key(prefix, identifier)
        try:
            await redis_client.redis.setex(
                key,
                expire,
                json.dumps(value)
            )
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")

cache_service = RedisCacheService()
