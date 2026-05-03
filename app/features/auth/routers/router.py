"""Auth API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.base import get_db
from app.features.auth.schemas.schema import (
    RegisterRequest,
    LoginRequest,
    RefreshRequest,
    TokenPair,
    UserResponse,
    PasswordResetRequest,
    PasswordResetConfirm,
)
from app.features.auth.services.service import (
    authenticate_user,
    create_user,
    create_company_and_hr,
    generate_token_pair,
    refresh_access_token,
    request_password_reset,
    confirm_password_reset,
)
from app.features.auth.dependencies.auth import get_current_user
from app.shared.schemas.response import StandardResponse
from app.shared.enums.user_roles import UserRole

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register/super-admin", response_model=StandardResponse[UserResponse])
async def register_super_admin(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    user = await create_user(db, data, role=UserRole.SUPER_ADMIN)
    return StandardResponse.ok(data=UserResponse.model_validate(user), message="Super admin registered")


@router.post("/register/hr", response_model=StandardResponse[dict])
async def register_hr(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    if not data.company_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="company_name is required for HR")
    hr, company = await create_company_and_hr(db, data)
    return StandardResponse.ok(
        data={
            "user": UserResponse.model_validate(hr),
            "company": {"id": company.id, "name": company.name, "slug": company.slug},
        },
        message="HR and company registered",
    )


@router.post("/register/applicant", response_model=StandardResponse[UserResponse])
async def register_applicant(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    user = await create_user(db, data, role=UserRole.APPLICANT)
    return StandardResponse.ok(data=UserResponse.model_validate(user), message="Applicant registered")


@router.post("/login", response_model=StandardResponse[TokenPair])
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, data.email, data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    tokens = await generate_token_pair(user)
    return StandardResponse.ok(data=tokens, message="Login successful")


@router.post("/refresh", response_model=StandardResponse[TokenPair])
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    tokens = await refresh_access_token(db, data.refresh_token)
    if not tokens:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    return StandardResponse.ok(data=tokens, message="Token refreshed")


@router.get("/me", response_model=StandardResponse[UserResponse])
async def me(current_user = Depends(get_current_user)):
    return StandardResponse.ok(data=UserResponse.model_validate(current_user))


@router.post("/password-reset/request", response_model=StandardResponse[dict])
async def password_reset_request(data: PasswordResetRequest, db: AsyncSession = Depends(get_db)):
    """Request password reset token.

    Token di-generate aman dan idealnya dikirim via email.
    NOTE: Email delivery belum aktif (perlu konfigurasi SMTP/SendGrid).
    """
    token = await request_password_reset(db, data.email)
    # Selalu kembalikan response yang sama untuk mencegah user enumeration
    response_data: dict = {"message": "Jika email terdaftar, link reset akan dikirim"}
    # TODO: Kirim token via email ke data.email
    # Untuk development: log token ke console (jangan di production!)
    if token:
        import structlog
        log = structlog.get_logger("auth.password_reset")
        log.info("Password reset token generated (dev only)", email=data.email, token=token)
    return StandardResponse.ok(data=response_data)


@router.post("/password-reset/confirm", response_model=StandardResponse[dict])
async def password_reset_confirm(data: PasswordResetConfirm, db: AsyncSession = Depends(get_db)):
    """Konfirmasi reset password menggunakan token.

    NOTE: Implementasi penuh butuh tabel password_reset_tokens via Alembic migration.
    """
    success = await confirm_password_reset(db, data.token, data.new_password)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token tidak valid, sudah digunakan, atau sudah kedaluwarsa",
        )
    return StandardResponse.ok(data={"message": "Password berhasil direset, silahkan login kembali"})
