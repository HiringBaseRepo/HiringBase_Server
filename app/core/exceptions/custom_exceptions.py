"""Custom exceptions for the HiringBase application."""

from app.shared.constants.errors import (
    ERR_AI_CONNECTION,
    ERR_AI_SERVER,
    ERR_APPLICATION_NOT_FOUND,
    ERR_COMPANY_NAME_REQUIRED,
    ERR_COMPANY_NOT_FOUND,
    ERR_DUPLICATE_APPLICATION,
    ERR_FIELD_NOT_FOUND,
    ERR_FILE_TOO_LARGE,
    ERR_INTERVIEW_NOT_FOUND,
    ERR_INVALID_CREDENTIALS,
    ERR_INVALID_FILE_TYPE,
    ERR_INVALID_REFRESH_TOKEN,
    ERR_INVALID_SETUP_TOKEN,
    ERR_JOB_NOT_FOUND,
    ERR_MISSING_DOCUMENTS,
    ERR_PASSWORD_RESET_TOKEN_INVALID,
    ERR_REFRESH_TOKEN_EXPIRED,
    ERR_RULE_NOT_FOUND,
    ERR_SCORING_TEMPLATE_MISSING,
    ERR_SECURITY_ALERT,
    ERR_TICKET_NOT_FOUND,
    ERR_TOKEN_REVOKED,
    ERR_TOKEN_ROTATION_FAILED,
    ERR_UNAUTHENTICATED,
    ERR_UNAUTHORIZED,
    ERR_USER_INACTIVE,
    ERR_USER_NOT_FOUND,
)
from app.shared.helpers.localization import get_label


class BaseDomainException(Exception):
    """Base class for all domain-specific exceptions."""
    pass


class RuleNotFoundException(BaseDomainException):
    """Raised when a knockout rule is not found."""

    def __init__(self, message: str = get_label(ERR_RULE_NOT_FOUND)):
        self.message = message
        super().__init__(self.message)


class ApplicationNotFoundException(BaseDomainException):
    """Raised when an application is not found."""

    def __init__(self, message: str = get_label(ERR_APPLICATION_NOT_FOUND)):
        self.message = message
        super().__init__(self.message)


class JobNotFoundException(BaseDomainException):
    """Raised when a job is not found."""

    def __init__(self, message: str = get_label(ERR_JOB_NOT_FOUND)):
        self.message = message
        super().__init__(self.message)


class UserNotFoundException(BaseDomainException):
    """Raised when a user is not found."""

    def __init__(self, message: str = get_label(ERR_USER_NOT_FOUND)):
        self.message = message
        super().__init__(self.message)


class InvalidCredentialsException(BaseDomainException):
    """Raised when user credentials are invalid."""

    def __init__(self, message: str = get_label(ERR_INVALID_CREDENTIALS)):
        self.message = message
        super().__init__(self.message)


class UserInactiveException(BaseDomainException):
    """Raised when a user is inactive."""

    def __init__(self, message: str = get_label(ERR_USER_INACTIVE)):
        self.message = message
        super().__init__(self.message)


class InvalidRefreshTokenException(BaseDomainException):
    """Raised when a refresh token is invalid."""

    def __init__(self, message: str = get_label(ERR_INVALID_REFRESH_TOKEN)):
        self.message = message
        super().__init__(self.message)


class RefreshTokenExpiredException(BaseDomainException):
    """Raised when a refresh token is expired."""

    def __init__(self, message: str = get_label(ERR_REFRESH_TOKEN_EXPIRED)):
        self.message = message
        super().__init__(self.message)


class TokenRevokedException(BaseDomainException):
    """Raised when a refresh token is revoked or already used."""

    def __init__(self, message: str = get_label(ERR_TOKEN_REVOKED)):
        self.message = message
        super().__init__(self.message)


class SecurityAlertException(BaseDomainException):
    """Raised when a security alert is triggered (e.g., token reuse)."""

    def __init__(self, message: str = get_label(ERR_SECURITY_ALERT)):
        self.message = message
        super().__init__(self.message)


class InvalidFileTypeException(BaseDomainException):
    """Raised when an invalid file type is uploaded."""

    def __init__(self, message: str = get_label(ERR_INVALID_FILE_TYPE)):
        self.message = message
        super().__init__(self.message)


class FileTooLargeException(BaseDomainException):
    """Raised when a file exceeds the maximum allowed size."""

    def __init__(self, message: str = get_label(ERR_FILE_TOO_LARGE)):
        self.message = message
        super().__init__(self.message)


class PasswordResetTokenInvalidException(BaseDomainException):
    """Raised when a password reset token is invalid or expired."""

    def __init__(
        self,
        message: str = get_label(ERR_PASSWORD_RESET_TOKEN_INVALID),
    ):
        self.message = message
        super().__init__(self.message)


class InvalidSetupTokenException(BaseDomainException):
    """Raised when setup token for super admin registration is invalid."""

    def __init__(self, message: str = get_label(ERR_INVALID_SETUP_TOKEN)):
        self.message = message
        super().__init__(self.message)


class CompanyNameRequiredException(BaseDomainException):
    """Raised when HR registration misses company name."""

    def __init__(self, message: str = get_label(ERR_COMPANY_NAME_REQUIRED)):
        self.message = message
        super().__init__(self.message)


class MissingDocumentsException(BaseDomainException):
    """Raised when required documents are missing."""

    def __init__(self, missing_docs: list[str], message: str | None = None):
        self.missing_docs = missing_docs
        self.message = message or f"{get_label(ERR_MISSING_DOCUMENTS)}: {', '.join(missing_docs)}"
        super().__init__(self.message)


class TokenRotationFailedException(BaseDomainException):
    """Raised when refresh token rotation fails."""

    def __init__(self, message: str = get_label(ERR_TOKEN_ROTATION_FAILED)):
        self.message = message
        super().__init__(self.message)


class DuplicateApplicationException(BaseDomainException):
    """Raised when a candidate tries to apply twice to the same job."""

    def __init__(self, message: str = get_label(ERR_DUPLICATE_APPLICATION)):
        self.message = message
        super().__init__(self.message)


class TicketNotFoundException(BaseDomainException):
    """Raised when a ticket is not found."""

    def __init__(self, message: str = get_label(ERR_TICKET_NOT_FOUND)):
        self.message = message
        super().__init__(self.message)


class TemplateNotFoundException(BaseDomainException):
    """Raised when a scoring template is not found."""

    def __init__(self, message: str = get_label(ERR_SCORING_TEMPLATE_MISSING)):
        self.message = message
        super().__init__(self.message)


class InterviewNotFoundException(BaseDomainException):
    """Raised when an interview is not found."""

    def __init__(self, message: str = get_label(ERR_INTERVIEW_NOT_FOUND)):
        self.message = message
        super().__init__(self.message)


class CompanyNotFoundException(BaseDomainException):
    """Raised when a company is not found."""

    def __init__(self, message: str = get_label(ERR_COMPANY_NOT_FOUND)):
        self.message = message
        super().__init__(self.message)


class FieldNotFoundException(BaseDomainException):
    """Raised when a form field is not found."""

    def __init__(self, message: str = get_label(ERR_FIELD_NOT_FOUND)):
        self.message = message
        super().__init__(self.message)


class WeightTotalInvalidException(BaseDomainException):
    """Raised when scoring weights do not sum to 100."""

    def __init__(self, total: float):
        self.total = total
        self.message = f"Total bobot harus 100, saat ini {total}"
        super().__init__(self.message)


class AIAPIException(BaseDomainException):
    """Base exception for external AI API errors."""

    pass


class AIAPIConnectionException(AIAPIException):
    """Raised on connection errors or timeouts."""

    def __init__(self, message: str = get_label(ERR_AI_CONNECTION)):
        self.message = message
        super().__init__(self.message)


class AIAPIServerException(AIAPIException):
    """Raised on 5xx errors from AI providers."""

    def __init__(self, message: str = get_label(ERR_AI_SERVER)):
        self.message = message
        super().__init__(self.message)


class UnauthenticatedException(BaseDomainException):
    """Raised when authentication is missing or invalid."""

    def __init__(self, message: str = get_label(ERR_UNAUTHENTICATED)):
        self.message = message
        super().__init__(self.message)


class UnauthorizedException(BaseDomainException):
    """Raised when a user lacks permission for an action."""

    def __init__(self, message: str = get_label(ERR_UNAUTHORIZED)):
        self.message = message
        super().__init__(self.message)
