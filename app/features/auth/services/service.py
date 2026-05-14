"""Auth business logic."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.hashing import get_password_hash, verify_password
from app.core.security.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.utils.ticket import generate_apply_code
from app.features.auth.repositories.repository import (
    delete_all_refresh_tokens_by_user_id,
    get_refresh_token_by_jti,
    get_user_by_email,
    get_user_by_id,
    save_company,
    save_refresh_token_record,
    save_user,
    soft_revoke_refresh_token,
)
from app.features.auth.schemas.schema import RegisterRequest, TokenPair
from app.features.companies.models import Company
from app.features.users.models import RefreshToken, User
from app.shared.enums.user_roles import UserRole
from app.core.exceptions import (
    InvalidCredentialsException,
    UserInactiveException,
    UserNotFoundException,
)
from app.features.audit_logs.models import AuditLog
from app.features.audit_logs.repositories.repository import create_audit_log
from app.shared.constants.audit_actions import (
    LOGIN_FAILURE,
    LOGIN_SUCCESS,
    LOGOUT,
    PASSWORD_RESET_REQUESTED,
)

# Moved RefreshToken to top

async def log_login_failure(db: AsyncSession, email: str) -> None:
    await create_audit_log(
        db,
        AuditLog(
            action=LOGIN_FAILURE,
            entity_type="auth",
            entity_id=0,
            new_values={"email": email}
        )
    )
    await db.commit()


async def authenticate_user(
    db: AsyncSession, email: str, password: str
) -> Optional[User]:
    user = await get_user_by_email(db, email)
    if not user or not user.password_hash:
        raise InvalidCredentialsException()
    if not verify_password(password, user.password_hash):
        raise InvalidCredentialsException()
    if not user.is_active:
        raise UserInactiveException()
    
    # Audit Log: Login Success
    await create_audit_log(
        db,
        AuditLog(
            company_id=user.company_id,
            user_id=user.id,
            action=LOGIN_SUCCESS,
            entity_type="auth",
            entity_id=user.id,
            new_values={"email": email}
        )
    )
    
    return user


async def create_user(
    db: AsyncSession, data: RegisterRequest, role: UserRole = UserRole.APPLICANT
) -> User:
    user = User(
        email=data.email,
        password_hash=get_password_hash(data.password),
        full_name=data.full_name,
        phone=data.phone,
        role=role,
    )
    user = await save_user(db, user)
    await db.commit()
    return user


async def create_company_and_hr(
    db: AsyncSession, data: RegisterRequest
) -> Tuple[User, Company]:
    company = Company(
        name=data.company_name or data.full_name + " Company",
        slug=generate_apply_code().replace("FRM-", "").lower(),
    )
    company = await save_company(db, company)

    hr = User(
        email=data.email,
        password_hash=get_password_hash(data.password),
        full_name=data.full_name,
        phone=data.phone,
        role=UserRole.HR,
        company_id=company.id,
    )
    hr = await save_user(db, hr)
    await db.commit()
    return hr, company


async def generate_token_pair(db: AsyncSession, user: User) -> TokenPair:
    jti = str(uuid.uuid4())
    payload_access = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value,
        "company_id": user.company_id,
        "token_version": user.token_version,
    }
    payload_refresh = {
        "sub": str(user.id),
        "jti": jti,
    }

    access = create_access_token(payload_access)
    refresh = create_refresh_token(payload_refresh)
    from app.core.config import settings

    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
    )

    refresh_token_record = RefreshToken(user_id=user.id, jti=jti, expires_at=expires_at)
    await save_refresh_token_record(db, refresh_token_record)
    await db.commit()

    return TokenPair(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


async def refresh_access_token(
    db: AsyncSession, refresh_token: str
) -> Optional[TokenPair]:
    from app.core.exceptions import (
        InvalidRefreshTokenException,
        RefreshTokenExpiredException,
        SecurityAlertException,
        UserInactiveException,
        TokenRotationFailedException,
    )

    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh" or not payload.get("jti"):
        raise InvalidRefreshTokenException("Struktur token tidak valid")

    sub = payload.get("sub")
    if not sub:
        raise InvalidRefreshTokenException("Token tidak memiliki identitas pengguna")
        
    try:
        user_id = int(sub)
    except (ValueError, TypeError):
        raise InvalidRefreshTokenException("Identitas pengguna tidak valid")
        
    jti = payload.get("jti")

    user = await get_user_by_id(db, user_id)
    if not user:
        raise UserNotFoundException()
    if not user.is_active:
        raise UserInactiveException()

    # Check DB for the refresh token
    token_record = await get_refresh_token_by_jti(db, jti)

    if not token_record:
        # Potential theft or already revoked/used.
        # Revoke all tokens for this user by incrementing token_version and deleting all their refresh tokens.
        user.token_version += 1
        await delete_all_refresh_tokens_by_user_id(db, user.id)
        await db.commit()
        raise SecurityAlertException()

    if token_record.is_revoked:
        # Grace period for multi-tab concurrency (30 seconds)
        if token_record.revoked_at:
            delta = datetime.now(timezone.utc) - token_record.revoked_at
            if delta.total_seconds() < 30:
                # Likely a concurrent request from another tab
                # We allow a new rotation but security alert is NOT triggered
                return await generate_token_pair(db, user)

        user.token_version += 1
        await delete_all_refresh_tokens_by_user_id(db, user.id)
        await db.commit()
        raise SecurityAlertException("Peringatan Keamanan: Token telah digunakan. Sesi Anda dihentikan demi keamanan.")

    if token_record.expires_at < datetime.now(timezone.utc):
        raise RefreshTokenExpiredException()

    # Rotate token
    try:
        # Use soft revoke instead of delete to support grace period
        await soft_revoke_refresh_token(db, token_record)
        # We don't commit yet, generate_token_pair will add the new one and commit
        tokens = await generate_token_pair(db, user)
        if not tokens:
             raise TokenRotationFailedException("Gagal menghasilkan pasangan token baru")
        return tokens
    except Exception as e:
        await db.rollback()
        import structlog
        logger = structlog.get_logger("auth.service")
        logger.error("token_rotation_failed", error=str(e), user_id=user.id)
        raise TokenRotationFailedException()


async def request_password_reset(db: AsyncSession, email: str) -> str | None:
    """Generate password reset token dan simpan hash ke DB.

    Returns:
        Plain token (to be sent via email), or None if user not found.
    """
    import hashlib
    import secrets

    user = await get_user_by_email(db, email)
    if not user:
        # Do not leak whether email exists
        return None

    # Generate secure token
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    # Store hash in temporary notes field (MVP — ideally use password_reset_tokens table)
    # Format: "PWRESET:<hash>:<expiry_unix>"
    import time

    expiry = int(time.time()) + 3600  # 1 hour
    user.notes = f"PWRESET:{token_hash}:{expiry}" if hasattr(user, "notes") else None  # type: ignore

    # Note: Production solution requires password_reset_tokens table.
    # MVP: Return token to be logged to console in the endpoint.
    
    # Audit Log
    await create_audit_log(
        db,
        AuditLog(
            company_id=user.company_id,
            user_id=user.id,
            action=PASSWORD_RESET_REQUESTED,
            entity_type="auth",
            entity_id=user.id,
            new_values={"email": email}
        )
    )
    
    await db.commit()
    return token


async def confirm_password_reset(
    db: AsyncSession, token: str, new_password: str
) -> bool:
    """Verify reset token and update user password.

    MVP: Since there is no dedicated table, this would match via secure query.
    Returns: True if successful, False if token invalid/expired.
    """
    # NOTE: Production implementation requires password_reset_tokens table with:
    # user_id, token_hash, expires_at, used_at
    # This MVP is a safe placeholder returning False
    # until the table is created via Alembic migration.
    return False


async def revoke_all_sessions(db: AsyncSession, user_id: int) -> bool:
    user = await get_user_by_id(db, user_id)
    if user:
        user.token_version += 1
        await delete_all_refresh_tokens_by_user_id(db, user_id)
        await db.commit()
    return True


async def logout(db: AsyncSession, user_id: int, jti: str) -> None:
    """Revoke a refresh token by its JTI with audit logging."""
    from app.features.auth.repositories.repository import revoke_refresh_token, get_user_by_id

    await revoke_refresh_token(db, jti)
    
    user = await get_user_by_id(db, user_id)
    
    # Audit Log
    await create_audit_log(
        db,
        AuditLog(
            company_id=user.company_id if user else None,
            user_id=user_id,
            action=LOGOUT,
            entity_type="auth",
            entity_id=user_id,
        )
    )
    
    await db.commit()
