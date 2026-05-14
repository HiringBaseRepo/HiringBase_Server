"""Application and runtime defaults."""

APP_NAME = "HiringBase"
APP_ENV = "development"
API_V1_PREFIX = "/api/v1"

DEFAULT_DEBUG = True
DEFAULT_SMTP_PORT = 587
DEFAULT_RATE_LIMIT_PER_MINUTE = 60

DEFAULT_CORS_ORIGINS = (
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    "https://hiringbase-webfrontend.boyblaco77.workers.dev",
)
