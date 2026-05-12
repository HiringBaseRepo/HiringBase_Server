"""Global exception handlers."""

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.config import settings
from app.core.exceptions import custom_exceptions as cex
from app.shared.schemas.response import StandardResponse
import structlog

logger = structlog.get_logger("core.exceptions")


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    logger.warning("Validation error", errors=exc.errors())
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=StandardResponse(
            success=False,
            message="Terjadi kesalahan validasi",
            errors=[{"loc": list(e["loc"]), "msg": e["msg"]} for e in exc.errors()],
        ).model_dump(),
    )


async def sqlalchemy_exception_handler(
    request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    logger.error("Database error", error=str(exc), exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=StandardResponse(
            success=False,
            message="Terjadi kesalahan pada database",
            errors=[{"error": str(exc)}],
        ).model_dump(),
    )


async def integrity_error_handler(
    request: Request, exc: IntegrityError
) -> JSONResponse:
    logger.warning("Data integrity conflict", error=str(exc.orig))
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=StandardResponse(
            success=False,
            message="Konflik data — kemungkinan data sudah ada",
            errors=[{"error": str(exc.orig)}],
        ).model_dump(),
    )

async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception", error=str(exc), exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=StandardResponse(
            success=False,
            message="Terjadi kesalahan internal pada server",
            errors=[{"error": str(exc)}]
            if settings.DEBUG
            else [{"error": "Terjadi kesalahan yang tidak terduga"}],
        ).model_dump(),
    )


async def domain_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle custom domain exceptions."""
    status_code = status.HTTP_400_BAD_REQUEST
    message = str(exc)

    if isinstance(
        exc,
        (
            cex.JobNotFoundException,
            cex.ApplicationNotFoundException,
            cex.UserNotFoundException,
            cex.RuleNotFoundException,
            cex.TicketNotFoundException,
            cex.TemplateNotFoundException,
            cex.InterviewNotFoundException,
            cex.CompanyNotFoundException,
            cex.FieldNotFoundException,
        ),
    ):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(
        exc,
        (
            cex.InvalidCredentialsException,
            cex.InvalidRefreshTokenException,
            cex.RefreshTokenExpiredException,
            cex.SecurityAlertException,
            cex.TokenRotationFailedException,
            cex.TokenRevokedException,
            cex.UnauthenticatedException,
        ),
    ):
        status_code = status.HTTP_401_UNAUTHORIZED
    elif isinstance(exc, cex.DuplicateApplicationException):
        status_code = status.HTTP_409_CONFLICT
    elif isinstance(
        exc,
        (
            cex.InvalidFileTypeException,
            cex.FileTooLargeException,
            cex.WeightTotalInvalidException,
            cex.PasswordResetTokenInvalidException,
        ),
    ):
        status_code = status.HTTP_400_BAD_REQUEST
    elif isinstance(exc, (cex.UserInactiveException, cex.UnauthorizedException)):
        status_code = status.HTTP_403_FORBIDDEN
    elif isinstance(exc, (cex.MissingDocumentsException, cex.AIAPIException)):
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY

    logger.info("Domain exception", status_code=status_code, message=message)
    return JSONResponse(
        status_code=status_code,
        content=StandardResponse.error(
            message=message,
            status_code=status_code
        ).model_dump(),
    )
