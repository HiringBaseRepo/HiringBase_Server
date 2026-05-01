"""Global exception handlers."""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from app.shared.schemas.response import StandardResponse


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=StandardResponse(
            success=False,
            message="Validation error",
            errors=[{"loc": e["loc"], "msg": e["msg"]} for e in exc.errors()],
        ).model_dump(),
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=StandardResponse(
            success=False,
            message="Database error occurred",
            errors=[str(exc)],
        ).model_dump(),
    )


async def integrity_error_handler(request: Request, exc: IntegrityError):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=StandardResponse(
            success=False,
            message="Resource conflict — possibly duplicate entry",
            errors=[str(exc.orig) if exc.orig else str(exc)],
        ).model_dump(),
    )


async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=StandardResponse(
            success=False,
            message="Internal server error",
            errors=[str(exc)] if settings.DEBUG else ["An unexpected error occurred"],
        ).model_dump(),
    )


from app.core.config import settings
