"""
Smart Resume Screening System — Main FastAPI Application
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database.base import engine, Base
from app.core.exceptions.handlers import (
    validation_exception_handler,
    sqlalchemy_exception_handler,
    integrity_error_handler,
    generic_exception_handler,
)
from app.core.middleware.rate_limit import RateLimitMiddleware
from app.shared.schemas.response import StandardResponse

# Routers
from app.features.auth.routers.router import router as auth_router
from app.features.companies.routers.router import router as companies_router
from app.features.users.routers.router import router as users_router
from app.features.jobs.routers.router import router as jobs_router
from app.features.job_forms.routers.router import router as job_forms_router
from app.features.scoring.routers.router import router as scoring_router
from app.features.applications.routers.router import router as applications_router
from app.features.documents.routers.router import router as documents_router
from app.features.screening.routers.router import router as screening_router
from app.features.ranking.routers.router import router as ranking_router
from app.features.tickets.routers.router import router as tickets_router
from app.features.notifications.routers.router import router as notifications_router
from app.features.interviews.routers.router import router as interviews_router
from app.features.audit_logs.routers.router import router as audit_logs_router
from app.features.screening.routers.manual_override import router as manual_override_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    if settings.APP_ENV == "development":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
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
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:5173", "http://127.0.0.1:3000"] if settings.DEBUG else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting
app.add_middleware(RateLimitMiddleware)

# Exception handlers
app.add_exception_handler(Exception, generic_exception_handler)
app.add_exception_handler(500, sqlalchemy_exception_handler)

# API Routers
app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
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
app.include_router(interviews_router, prefix=settings.API_V1_PREFIX)
app.include_router(audit_logs_router, prefix=settings.API_V1_PREFIX)
app.include_router(manual_override_router, prefix=settings.API_V1_PREFIX)


@app.get("/", tags=["Health"])
async def root():
    return StandardResponse.ok(data={"app": settings.APP_NAME, "version": "1.0.0"})


@app.get("/health", tags=["Health"])
async def health_check():
    return StandardResponse.ok(data={"status": "healthy"})
