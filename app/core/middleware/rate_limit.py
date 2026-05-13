"""Rate limiting middleware (simple in-memory)."""
import time
from typing import Dict

from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings
from app.shared.helpers.localization import get_label
from app.shared.schemas.response import StandardResponse

client_requests: Dict[str, list] = {}


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if settings.APP_ENV == "test":
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window = 60  # seconds
        limit = settings.RATE_LIMIT_PER_MINUTE

        reqs = client_requests.get(client_ip, [])
        reqs = [t for t in reqs if now - t < window]
        reqs.append(now)
        client_requests[client_ip] = reqs

        if len(reqs) > limit:
            payload = StandardResponse.error(
                message=get_label("Terlalu banyak permintaan, coba lagi dalam 1 menit."),
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content=payload.model_dump(),
            )

        return await call_next(request)
