"""Rate limiting middleware (Redis-backed sliding window)."""

import time
from typing import Dict, Optional

import structlog
from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.cache.client import redis_client
from app.core.config import settings
from app.shared.constants.errors import ERR_RATE_LIMIT
from app.shared.helpers.localization import get_label
from app.shared.schemas.response import StandardResponse

logger = structlog.get_logger("middleware.rate_limit")

_WINDOW = 60
_TTL = 120
_REDIS_PREFIX = "ratelimit:"
_FALLBACK_MAX_ENTRIES = 10_000

_fallback_store: Dict[str, list] = {}


def _extract_client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _redis_key(client_ip: str) -> str:
    return f"{_REDIS_PREFIX}{client_ip}"


def _build_429() -> JSONResponse:
    payload = StandardResponse.error(
        message=get_label(ERR_RATE_LIMIT),
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
    )
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content=payload.model_dump(),
    )


async def _is_exceeded(client_ip: str, limit: int) -> bool:
    """Check rate limit via Redis sorted-set sliding window.

    Returns ``True`` when the client has exceeded *limit* requests inside
    the sliding window.  Falls back to an in-memory store when Redis is
    unavailable.
    """
    redis = redis_client.redis

    if redis:
        key = _redis_key(client_ip)
        now = time.time()
        cutoff = now - _WINDOW

        try:
            await redis.zremrangebyscore(key, "-inf", cutoff)
            count = await redis.zcard(key)

            if count >= limit:
                return True

            await redis.zadd(key, {str(now): now})
            await redis.expire(key, _TTL)
            return False
        except Exception:
            logger.warning("rate_limit_redis_failed", client_ip=client_ip)

    now = time.time()
    reqs = _fallback_store.get(client_ip, [])
    reqs = [t for t in reqs if now - t < _WINDOW]
    reqs.append(now)
    _fallback_store[client_ip] = reqs

    if len(_fallback_store) > _FALLBACK_MAX_ENTRIES:
        _fallback_store.clear()

    return len(reqs) > limit


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if settings.APP_ENV == "test":
            return await call_next(request)

        client_ip = _extract_client_ip(request)
        limit = settings.RATE_LIMIT_PER_MINUTE

        if await _is_exceeded(client_ip, limit):
            return _build_429()

        return await call_next(request)
