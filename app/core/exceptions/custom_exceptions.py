"""Custom exceptions for the HireBase application."""


class RuleNotFoundException(Exception):
    """Raised when a knockout rule is not found."""

    def __init__(self, message: str = "Knockout rule not found"):
        self.message = message
        super().__init__(self.message)


class ApplicationNotFoundException(Exception):
    """Raised when an application is not found."""

    def __init__(self, message: str = "Application not found"):
        self.message = message
        super().__init__(self.message)


class JobNotFoundException(Exception):
    """Raised when a job is not found."""

    def __init__(self, message: str = "Job not found"):
        self.message = message
        super().__init__(self.message)


class UserNotFoundException(Exception):
    """Raised when a user is not found."""

    def __init__(self, message: str = "User not found"):
        self.message = message
        super().__init__(self.message)


class InvalidCredentialsException(Exception):
    """Raised when user credentials are invalid."""

    def __init__(self, message: str = "Invalid credentials"):
        self.message = message
        super().__init__(self.message)


class UserInactiveException(Exception):
    """Raised when a user is inactive."""

    def __init__(self, message: str = "User is inactive"):
        self.message = message
        super().__init__(self.message)


class InvalidRefreshTokenException(Exception):
    """Raised when a refresh token is invalid."""

    def __init__(self, message: str = "Invalid refresh token"):
        self.message = message
        super().__init__(self.message)


class RefreshTokenExpiredException(Exception):
    """Raised when a refresh token is expired."""

    def __init__(self, message: str = "Refresh token expired"):
        self.message = message
        super().__init__(self.message)


class TokenRevokedException(Exception):
    """Raised when a refresh token is revoked or already used."""

    def __init__(self, message: str = "Token was revoked or already used"):
        self.message = message
        super().__init__(self.message)


class SecurityAlertException(Exception):
    """Raised when a security alert is triggered (e.g., token reuse)."""

    def __init__(self, message: str = "Security Alert: Please login again"):
        self.message = message
        super().__init__(self.message)


class InvalidFileTypeException(Exception):
    """Raised when an invalid file type is uploaded."""

    def __init__(self, message: str = "Invalid file type"):
        self.message = message
        super().__init__(self.message)


class FileTooLargeException(Exception):
    """Raised when a file exceeds the maximum allowed size."""

    def __init__(self, message: str = "File too large"):
        self.message = message
        super().__init__(self.message)


class PasswordResetTokenInvalidException(Exception):
    """Raised when a password reset token is invalid or expired."""

    def __init__(
        self,
        message: str = "Token tidak valid, sudah digunakan, atau sudah kedaluwarsa",
    ):
        self.message = message
        super().__init__(self.message)


class MissingDocumentsException(Exception):
    """Raised when required documents are missing."""

    def __init__(self, missing_docs: list[str], message: str | None = None):
        self.missing_docs = missing_docs
        self.message = message or f"Missing documents: {', '.join(missing_docs)}"
        super().__init__(self.message)
