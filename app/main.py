"""
Hiringbase — Main FastAPI Application
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import FileResponse, PlainTextResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.config import settings
from app.core.database.base import Base, engine
from app.features.models import *  # noqa: F401,F403 — register all models
from app.core.exceptions.custom_exceptions import BaseDomainException
from app.core.exceptions.handlers import (
    domain_exception_handler,
    generic_exception_handler,
    integrity_error_handler,
    sqlalchemy_exception_handler,
    validation_exception_handler,
)
from app.core.logging import setup_logging
from app.core.middleware.logging import LoggingMiddleware
from app.core.middleware.rate_limit import RateLimitMiddleware
from app.features.applications.routers.router import router as applications_router
from app.features.audit_logs.routers.router import router as audit_logs_router
from app.features.dashboard.routers.router import router as dashboard_router

# Routers
from app.features.auth.routers.router import router as auth_router
from app.features.companies.routers.router import router as companies_router
from app.features.documents.routers.router import router as documents_router
from app.features.interviews.routers.router import router as interviews_router
from app.features.job_forms.routers.router import router as job_forms_router
from app.features.jobs.routers.router import router as jobs_router
from app.features.notifications.routers.router import router as notifications_router
from app.features.reports.routers.router import router as reports_router
from app.features.ranking.routers.router import router as ranking_router
from app.features.scoring.routers.router import router as scoring_router
from app.features.screening.routers.manual_override import (
    router as manual_override_router,
)
from app.features.screening.routers.router import router as screening_router
from app.features.tickets.routers.router import router as tickets_router
from app.features.users.routers.router import router as users_router
from app.features.big_data.routers.router import router as big_data_router
from app.shared.schemas.response import StandardResponse

# Initialize Logging
setup_logging()

from app.core.tkq import broker  # noqa: E402
import app.features.screening.tasks  # noqa: F401,E402
import app.shared.tasks.mail_tasks  # noqa: F401,E402
from app.core.cache.client import redis_client  # noqa: E402

_BANNER = r"""
╔══════════════════════════════════════════════════════╗
║                                                      ║
║      █░█ █ █▀█ █ █▄░█ █▀▀ █▄▄ ▄▀█ █▀ █▀▀             ║
║      █▀█ █ █▀▄ █ █░▀█ █▄█ █▄█ █▀█ ▄█ ██▄             ║
║                                                      ║
║          HiringBase AI Recruitment System            ║
║                Backend API v1.0                      ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
"""

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    try:
        print(_BANNER)
    except Exception:
        print("HiringBase Backend API v1.0")
    # Startup Redis
    await redis_client.connect()
    
    # Startup Taskiq Broker
    if not broker.is_worker_process:
        await broker.startup()

    # Startup MongoDB
    from app.core.database.mongo import connect_mongo, disconnect_mongo
    await connect_mongo()

    if settings.APP_ENV == "development":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
    yield
    
    # Shutdown
    if not broker.is_worker_process:
        await broker.shutdown()

    # Shutdown Redis
    await redis_client.disconnect()

    # Shutdown MongoDB
    await disconnect_mongo()

    if settings.APP_ENV != "testing":
        await engine.dispose()



app = FastAPI(
    title=settings.APP_NAME,
    description="AI-Based Recruitment Assistant Backend API",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging & Rate limiting
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware)

# Exception handlers
app.add_exception_handler(Exception, generic_exception_handler)  # type: ignore[misc]
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)  # type: ignore[misc]
app.add_exception_handler(IntegrityError, integrity_error_handler)  # type: ignore[misc]
app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[misc]
app.add_exception_handler(BaseDomainException, domain_exception_handler)  # type: ignore[misc]

# API Routers
app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(dashboard_router, prefix=settings.API_V1_PREFIX)
app.include_router(companies_router, prefix=settings.API_V1_PREFIX)
app.include_router(users_router, prefix=settings.API_V1_PREFIX)
app.include_router(jobs_router, prefix=settings.API_V1_PREFIX)
app.include_router(job_forms_router, prefix=settings.API_V1_PREFIX)
app.include_router(scoring_router, prefix=settings.API_V1_PREFIX)
app.include_router(applications_router, prefix=settings.API_V1_PREFIX)
app.include_router(documents_router, prefix=settings.API_V1_PREFIX)
app.include_router(screening_router, prefix=settings.API_V1_PREFIX)
app.include_router(ranking_router, prefix=settings.API_V1_PREFIX)
app.include_router(tickets_router, prefix=settings.API_V1_PREFIX)
app.include_router(notifications_router, prefix=settings.API_V1_PREFIX)
app.include_router(reports_router, prefix=settings.API_V1_PREFIX)
app.include_router(interviews_router, prefix=settings.API_V1_PREFIX)
app.include_router(audit_logs_router, prefix=settings.API_V1_PREFIX)
app.include_router(manual_override_router, prefix=settings.API_V1_PREFIX)
app.include_router(big_data_router, prefix=settings.API_V1_PREFIX)



BASE_DIR = Path(__file__).resolve().parent.parent
FAVICON_PATH = BASE_DIR / "assets" / "favicon" / "fAVICON hR.png"
FAVICON_EXISTS = FAVICON_PATH.exists()


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    if not FAVICON_EXISTS:
        return PlainTextResponse("Favicon not found", status_code=404)
    return FileResponse(FAVICON_PATH)


if settings.DEBUG:
    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        return get_swagger_ui_html(
            openapi_url=app.openapi_url,  # type: ignore
            title=app.title + " - Swagger UI",
            oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
            swagger_favicon_url="/favicon.ico?v=1",
        )

    @app.get("/redoc", include_in_schema=False)
    async def custom_redoc_html():
        return get_redoc_html(
            openapi_url=app.openapi_url,  # type: ignore
            title=app.title + " - ReDoc",
            redoc_favicon_url="/favicon.ico?v=1",
        )


@app.api_route("/", methods=["GET", "HEAD"], tags=["Health"])
async def root():
    return PlainTextResponse(_BANNER)


@app.api_route("/health", methods=["GET", "HEAD"], tags=["Health"])
async def health_check():
    return StandardResponse.ok(data={"status": "healthy"})
