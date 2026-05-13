"""Custom exceptions for the HiringBase application."""


class BaseDomainException(Exception):
    """Base class for all domain-specific exceptions."""
    pass


class RuleNotFoundException(BaseDomainException):
    """Raised when a knockout rule is not found."""

    def __init__(self, message: str = "Aturan knockout tidak ditemukan"):
        self.message = message
        super().__init__(self.message)


class ApplicationNotFoundException(BaseDomainException):
    """Raised when an application is not found."""

    def __init__(self, message: str = "Lamaran tidak ditemukan"):
        self.message = message
        super().__init__(self.message)


class JobNotFoundException(BaseDomainException):
    """Raised when a job is not found."""

    def __init__(self, message: str = "Lowongan tidak ditemukan"):
        self.message = message
        super().__init__(self.message)


class UserNotFoundException(BaseDomainException):
    """Raised when a user is not found."""

    def __init__(self, message: str = "Pengguna tidak ditemukan"):
        self.message = message
        super().__init__(self.message)


class InvalidCredentialsException(BaseDomainException):
    """Raised when user credentials are invalid."""

    def __init__(self, message: str = "Email atau password salah"):
        self.message = message
        super().__init__(self.message)


class UserInactiveException(BaseDomainException):
    """Raised when a user is inactive."""

    def __init__(self, message: str = "Akun tidak aktif"):
        self.message = message
        super().__init__(self.message)


class InvalidRefreshTokenException(BaseDomainException):
    """Raised when a refresh token is invalid."""

    def __init__(self, message: str = "Refresh token tidak valid"):
        self.message = message
        super().__init__(self.message)


class RefreshTokenExpiredException(BaseDomainException):
    """Raised when a refresh token is expired."""

    def __init__(self, message: str = "Sesi telah berakhir, silakan login kembali"):
        self.message = message
        super().__init__(self.message)


class TokenRevokedException(BaseDomainException):
    """Raised when a refresh token is revoked or already used."""

    def __init__(self, message: str = "Token telah dicabut atau sudah digunakan"):
        self.message = message
        super().__init__(self.message)


class SecurityAlertException(BaseDomainException):
    """Raised when a security alert is triggered (e.g., token reuse)."""

    def __init__(self, message: str = "Peringatan Keamanan: Silakan login kembali"):
        self.message = message
        super().__init__(self.message)


class InvalidFileTypeException(BaseDomainException):
    """Raised when an invalid file type is uploaded."""

    def __init__(self, message: str = "Format file tidak didukung"):
        self.message = message
        super().__init__(self.message)


class FileTooLargeException(BaseDomainException):
    """Raised when a file exceeds the maximum allowed size."""

    def __init__(self, message: str = "Ukuran file terlalu besar"):
        self.message = message
        super().__init__(self.message)


class PasswordResetTokenInvalidException(BaseDomainException):
    """Raised when a password reset token is invalid or expired."""

    def __init__(
        self,
        message: str = "Token reset password tidak valid atau sudah kedaluwarsa",
    ):
        self.message = message
        super().__init__(self.message)


class InvalidSetupTokenException(BaseDomainException):
    """Raised when setup token for super admin registration is invalid."""

    def __init__(self, message: str = "Setup token tidak valid atau belum diatur di .env"):
        self.message = message
        super().__init__(self.message)


class CompanyNameRequiredException(BaseDomainException):
    """Raised when HR registration misses company name."""

    def __init__(self, message: str = "Nama perusahaan wajib diisi untuk HR"):
        self.message = message
        super().__init__(self.message)


class MissingDocumentsException(BaseDomainException):
    """Raised when required documents are missing."""

    def __init__(self, missing_docs: list[str], message: str | None = None):
        self.missing_docs = missing_docs
        self.message = message or f"Dokumen wajib belum diunggah: {', '.join(missing_docs)}"
        super().__init__(self.message)


class TokenRotationFailedException(BaseDomainException):
    """Raised when refresh token rotation fails."""

    def __init__(self, message: str = "Gagal memperbarui sesi (token rotation)"):
        self.message = message
        super().__init__(self.message)


class DuplicateApplicationException(BaseDomainException):
    """Raised when a candidate tries to apply twice to the same job."""

    def __init__(self, message: str = "Anda sudah melamar untuk lowongan ini"):
        self.message = message
        super().__init__(self.message)


class TicketNotFoundException(BaseDomainException):
    """Raised when a ticket is not found."""

    def __init__(self, message: str = "Tiket tidak ditemukan"):
        self.message = message
        super().__init__(self.message)


class TemplateNotFoundException(BaseDomainException):
    """Raised when a scoring template is not found."""

    def __init__(self, message: str = "Template penilaian tidak ditemukan"):
        self.message = message
        super().__init__(self.message)


class InterviewNotFoundException(BaseDomainException):
    """Raised when an interview is not found."""

    def __init__(self, message: str = "Wawancara tidak ditemukan"):
        self.message = message
        super().__init__(self.message)


class CompanyNotFoundException(BaseDomainException):
    """Raised when a company is not found."""

    def __init__(self, message: str = "Perusahaan tidak ditemukan"):
        self.message = message
        super().__init__(self.message)


class FieldNotFoundException(BaseDomainException):
    """Raised when a form field is not found."""

    def __init__(self, message: str = "Field tidak ditemukan"):
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

    def __init__(self, message: str = "Gagal terhubung ke API AI (Timeout/Network)"):
        self.message = message
        super().__init__(self.message)


class AIAPIServerException(AIAPIException):
    """Raised on 5xx errors from AI providers."""

    def __init__(self, message: str = "Server API AI sedang bermasalah (5xx)"):
        self.message = message
        super().__init__(self.message)


class UnauthenticatedException(BaseDomainException):
    """Raised when authentication is missing or invalid."""

    def __init__(self, message: str = "Otentikasi diperlukan"):
        self.message = message
        super().__init__(self.message)


class UnauthorizedException(BaseDomainException):
    """Raised when a user lacks permission for an action."""

    def __init__(self, message: str = "Anda tidak memiliki akses untuk melakukan tindakan ini"):
        self.message = message
        super().__init__(self.message)
