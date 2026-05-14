"""Auth API endpoints."""

from fastapi import APIRouter, Request, Response

from app.core.config import settings
from app.core.exceptions import (
    CompanyNameRequiredException,
    InvalidCredentialsException,
    InvalidRefreshTokenException,
    InvalidSetupTokenException,
    PasswordResetTokenInvalidException,
)
from app.features.auth.dependencies.auth import CurrentUserDep, DbDep
from app.features.auth.schemas.schema import (
    AccessTokenResponse,
    LoginRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RegisterRequest,
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
from app.shared.constants.errors import (
    ERR_REFRESH_TOKEN_NOT_FOUND,
    ERR_REFRESH_TOKEN_EXPIRED,
)
from app.shared.helpers.localization import get_label

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _refresh_cookie_kwargs() -> dict[str, object]:
    return {
        "httponly": True,
        "secure": settings.AUTH_COOKIE_SECURE,
        "samesite": settings.AUTH_COOKIE_SAMESITE_EFFECTIVE,
        "path": settings.AUTH_COOKIE_PATH,
        "domain": settings.AUTH_COOKIE_DOMAIN,
    }


@router.post("/register/super-admin", response_model=StandardResponse[UserResponse])
async def register_super_admin(
    data: RegisterRequest, 
    request: Request,
    db: DbDep,
):
    """
    Register initial super admin.
    Requires 'X-Setup-Token' header matching SETUP_TOKEN in .env.
    """
    setup_token = request.headers.get("X-Setup-Token")
    if not settings.SETUP_TOKEN or setup_token != settings.SETUP_TOKEN:
        raise InvalidSetupTokenException()
        
    user = await create_user(db, data, role=UserRole.SUPER_ADMIN)
    return StandardResponse.ok(
        data=UserResponse.model_validate(user), message=get_label("Super admin registered")
    )


@router.post("/register/hr", response_model=StandardResponse[dict])
async def register_hr(data: RegisterRequest, db: DbDep):
    if not data.company_name:
        raise CompanyNameRequiredException()
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
    data: LoginRequest, response: Response, db: DbDep
):
    try:
        user = await authenticate_user(db, data.email, data.password)
        if not user:
            raise InvalidCredentialsException()
    except InvalidCredentialsException as e:
        from app.features.auth.services.service import log_login_failure
        await log_login_failure(db, data.email)
        raise e
    tokens = await generate_token_pair(db, user)

    response.set_cookie(
        key="refresh_token",
        value=tokens.refresh_token,
        **_refresh_cookie_kwargs(),
    )

    response_data = AccessTokenResponse(
        access_token=tokens.access_token, expires_in=tokens.expires_in
    )
    return StandardResponse.ok(data=response_data, message=get_label("Login successful"))


@router.post("/refresh", response_model=StandardResponse[AccessTokenResponse])
async def refresh(
    response: Response, request: Request, db: DbDep
):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise InvalidRefreshTokenException(get_label(ERR_REFRESH_TOKEN_NOT_FOUND))

    tokens = await refresh_access_token(db, refresh_token)
    if not tokens:
        raise InvalidRefreshTokenException(get_label(ERR_REFRESH_TOKEN_EXPIRED))

    response.set_cookie(
        key="refresh_token",
        value=tokens.refresh_token,
        **_refresh_cookie_kwargs(),
    )

    response_data = AccessTokenResponse(
        access_token=tokens.access_token, expires_in=tokens.expires_in
    )
    return StandardResponse.ok(data=response_data, message=get_label("Token refreshed"))


@router.post("/logout", response_model=StandardResponse[dict])
async def logout(
    response: Response, request: Request, db: DbDep
):
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        from app.core.security.jwt import decode_token

        payload = decode_token(refresh_token)
        if payload and payload.get("jti") and payload.get("sub"):
            jti = payload.get("jti")
            user_id = int(payload.get("sub"))
            await logout_service(db, user_id, jti)

    response.delete_cookie(
        key="refresh_token",
        path=settings.AUTH_COOKIE_PATH,
        domain=settings.AUTH_COOKIE_DOMAIN,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE_EFFECTIVE,
    )
    return StandardResponse.ok(
        data={"message": get_label("Logout successful")}, message=get_label("Logged out")
    )


@router.get("/me", response_model=StandardResponse[UserResponse])
async def me(current_user: CurrentUserDep):
    return StandardResponse.ok(data=UserResponse.model_validate(current_user))


@router.post("/password-reset/request", response_model=StandardResponse[dict])
async def password_reset_request(
    data: PasswordResetRequest, db: DbDep
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
    data: PasswordResetConfirm, db: DbDep
):
    """Konfirmasi reset password menggunakan token."""
    success = await confirm_password_reset(db, data.token, data.new_password)
    if not success:
        raise PasswordResetTokenInvalidException()
    return StandardResponse.ok(
        data={"message": "Password berhasil direset, silahkan login kembali"}
    )
