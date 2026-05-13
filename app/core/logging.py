import logging
import sys
import structlog
from structlog.processors import (
    dict_tracebacks,
    format_exc_info,
    JSONRenderer,
    StackInfoRenderer,
)
from app.core.config import settings

def setup_logging():
    """Configures structlog based on environment."""
    
    # Processors that don't depend on the underlying logger type
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ]

    if settings.APP_ENV == "development" and sys.stderr.isatty():
        # Human-friendly logging for development
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    else:
        # Structured JSON logging for production
        processors = shared_processors + [
            structlog.stdlib.add_logger_name,
            StackInfoRenderer(),
            format_exc_info,
            dict_tracebacks,
            JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure the standard library logging to use structlog's LoggerFactory
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    )
