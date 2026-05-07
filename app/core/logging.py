import logging
import sys
import structlog
from structlog.processors import (
    add_log_level,
    dict_tracebacks,
    format_exc_info,
    JSONRenderer,
    TimeStamper,
    StackInfoRenderer,
)
from app.core.config import settings

def setup_logging():
    """Configures structlog based on environment."""
    
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        add_log_level,
        structlog.stdlib.add_logger_name,
        TimeStamper(fmt="iso", utc=True),
    ]

    if settings.APP_ENV == "development" and sys.stderr.isatty():
        # Human-friendly logging for development
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    else:
        # Structured JSON logging for production
        processors = shared_processors + [
            StackInfoRenderer(),
            format_exc_info,
            dict_tracebacks,
            JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Bridge standard logging to structlog if needed
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    )
