"""
Hiringbase — Main FastAPI Application
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
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
from app.shared.schemas.response import StandardResponse

# Initialize Logging
setup_logging()

from app.core.tkq import broker
import app.features.screening.tasks  # noqa: F401
import app.shared.tasks.mail_tasks  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup Taskiq Broker


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup Taskiq Broker
    if not broker.is_worker_process:
        await broker.startup()

    if settings.APP_ENV == "development":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
    if not broker.is_worker_process:
        await broker.startup()

    if settings.APP_ENV == "development":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
    if not broker.is_worker_process:
        await broker.shutdown()

    if settings.APP_ENV != "testing":
        await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    description="AI-Based Recruitment Assistant Backend API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]
    if settings.DEBUG
    else [],
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


@app.get("/", tags=["Health"])
async def root():
    return StandardResponse.ok(data={"app": settings.APP_NAME, "version": "1.0.0"})


@app.get("/health", tags=["Health"])
async def health_check():
    return StandardResponse.ok(data={"status": "healthy"})
