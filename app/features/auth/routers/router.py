"""Auth API endpoints."""

from fastapi import (
    APIRouter,
    Depends,
    Request,
    Response,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database.base import get_db
from app.core.exceptions import (
    InvalidCredentialsException,
    InvalidRefreshTokenException,
    RefreshTokenExpiredException,
    SecurityAlertException,
    UserInactiveException,
    UserNotFoundException,
)
from app.features.auth.dependencies.auth import get_current_user
from app.features.auth.schemas.schema import (
    AccessTokenResponse,
    LoginRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
    UserResponse,
)
from app.features.auth.services.service import (
    authenticate_user,
    confirm_password_reset,
    create_company_and_hr,
    create_user,
    generate_token_pair,
    refresh_access_token,
    request_password_reset,
    logout as logout_service,
)
from app.shared.enums.user_roles import UserRole
from app.shared.schemas.response import StandardResponse
from app.shared.helpers.localization import get_label

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register/super-admin", response_model=StandardResponse[UserResponse])
async def register_super_admin(
    data: RegisterRequest, 
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Register initial super admin.
    Requires 'X-Setup-Token' header matching SETUP_TOKEN in .env.
    """
    setup_token = request.headers.get("X-Setup-Token")
    if not settings.SETUP_TOKEN or setup_token != settings.SETUP_TOKEN:
        raise BaseDomainException("Setup token tidak valid atau belum diatur di .env")
        
    user = await create_user(db, data, role=UserRole.SUPER_ADMIN)
    return StandardResponse.ok(
        data=UserResponse.model_validate(user), message=get_label("Super admin registered")
    )


@router.post("/register/hr", response_model=StandardResponse[dict])
async def register_hr(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    if not data.company_name:
        raise BaseDomainException("Nama perusahaan wajib diisi untuk HR")
    hr, company = await create_company_and_hr(db, data)
    return StandardResponse.ok(
        data={
            "user": UserResponse.model_validate(hr),
            "company": {"id": company.id, "name": company.name, "slug": company.slug},
        },
        message=get_label("HR and company registered"),
    )


@router.post("/login", response_model=StandardResponse[AccessTokenResponse])
async def login(
    data: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)
):
    try:
        user = await authenticate_user(db, data.email, data.password)
        if not user:
            raise InvalidCredentialsException()
    except InvalidCredentialsException as e:
        # Audit Log: Login Failure
        from app.features.audit_logs.models import AuditLog
        from app.features.audit_logs.repositories.repository import create_audit_log
        await create_audit_log(
            db,
            AuditLog(
                action="LOGIN_FAILURE",
                entity_type="auth",
                entity_id=0,
                new_values={"email": data.email}
            )
        )
        await db.commit()
        raise e
    tokens = await generate_token_pair(db, user)

    response.set_cookie(
        key="refresh_token",
        value=tokens.refresh_token,
        httponly=True,
        secure=settings.APP_ENV == "production",
        samesite="lax",
    )

    response_data = AccessTokenResponse(
        access_token=tokens.access_token, expires_in=tokens.expires_in
    )
    return StandardResponse.ok(data=response_data, message=get_label("Login successful"))


@router.post("/refresh", response_model=StandardResponse[AccessTokenResponse])
async def refresh(
    response: Response, request: Request, db: AsyncSession = Depends(get_db)
):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise InvalidRefreshTokenException("Refresh token tidak ditemukan di cookies")

    tokens = await refresh_access_token(db, refresh_token)
    if not tokens:
        raise InvalidRefreshTokenException("Gagal memperbarui sesi, silakan login kembali")

    response.set_cookie(
        key="refresh_token",
        value=tokens.refresh_token,
        httponly=True,
        secure=settings.APP_ENV == "production",
        samesite="lax",
    )

    response_data = AccessTokenResponse(
        access_token=tokens.access_token, expires_in=tokens.expires_in
    )
    return StandardResponse.ok(data=response_data, message=get_label("Token refreshed"))


@router.post("/logout", response_model=StandardResponse[dict])
async def logout(
    response: Response, request: Request, db: AsyncSession = Depends(get_db)
):
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        from app.core.security.jwt import decode_token

        payload = decode_token(refresh_token)
        if payload and payload.get("jti"):
            jti = payload.get("jti")
            await logout_service(db, current_user.id, jti)

    response.delete_cookie(key="refresh_token")
    return StandardResponse.ok(
        data={"message": get_label("Logout successful")}, message=get_label("Logged out")
    )


@router.get("/me", response_model=StandardResponse[UserResponse])
async def me(current_user=Depends(get_current_user)):
    return StandardResponse.ok(data=UserResponse.model_validate(current_user))


@router.post("/password-reset/request", response_model=StandardResponse[dict])
async def password_reset_request(
    data: PasswordResetRequest, db: AsyncSession = Depends(get_db)
):
    """Request password reset token."""
    token = await request_password_reset(db, data.email)
    response_data: dict = {"message": "Jika email terdaftar, link reset akan dikirim"}
    if token:
        import structlog
        log = structlog.get_logger("auth.password_reset")
        log.info(
            "Password reset token generated (dev only)", email=data.email, token=token
        )
    return StandardResponse.ok(data=response_data)


@router.post("/password-reset/confirm", response_model=StandardResponse[dict])
async def password_reset_confirm(
    data: PasswordResetConfirm, db: AsyncSession = Depends(get_db)
):
    """Konfirmasi reset password menggunakan token."""
    success = await confirm_password_reset(db, data.token, data.new_password)
    if not success:
        raise PasswordResetTokenInvalidException()
    return StandardResponse.ok(
        data={"message": "Password berhasil direset, silahkan login kembali"}
    )
