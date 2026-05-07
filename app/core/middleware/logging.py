import uuid
import time
import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = structlog.get_logger("middleware.logging")

class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to add request_id and log request/response details."""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        start_time = time.time()
        
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            # Log successful requests
            logger.info(
                "Request processed",
                status_code=response.status_code,
                duration=f"{duration:.4f}s",
            )
            
            response.headers["X-Request-ID"] = request_id
            return response
            
        except Exception as exc:
            duration = time.time() - start_time
            logger.error(
                "Request failed",
                error=str(exc),
                duration=f"{duration:.4f}s",
            )
            raise exc
