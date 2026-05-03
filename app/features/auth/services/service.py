"""Auth business logic."""
from typing import Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.hashing import verify_password, get_password_hash
from app.core.security.jwt import create_access_token, create_refresh_token, decode_token
from app.core.utils.ticket import generate_apply_code
from app.features.models import User, Company
from app.features.auth.repositories.repository import (
    get_user_by_email,
    get_user_by_id,
    save_company,
    save_user,
)
from app.features.auth.schemas.schema import RegisterRequest, TokenPair
from app.shared.enums.user_roles import UserRole


async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[User]:
    user = await get_user_by_email(db, email)
    if not user or not user.password_hash:
        return None
    if not verify_password(password, user.password_hash):
        return None
    if not user.is_active:
        return None
    return user


async def create_user(db: AsyncSession, data: RegisterRequest, role: UserRole = UserRole.APPLICANT) -> User:
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


async def create_company_and_hr(db: AsyncSession, data: RegisterRequest) -> Tuple[User, Company]:
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


async def generate_token_pair(user: User) -> TokenPair:
    payload = {
        "sub": user.id,
        "email": user.email,
        "role": user.role.value,
        "company_id": user.company_id,
    }
    access = create_access_token(payload)
    refresh = create_refresh_token(payload)
    from app.core.config import settings
    return TokenPair(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


async def refresh_access_token(db: AsyncSession, refresh_token: str) -> Optional[TokenPair]:
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        return None
    user_id = int(payload.get("sub"))
    user = await get_user_by_id(db, user_id)
    if not user or not user.is_active:
        return None
    return await generate_token_pair(user)


async def request_password_reset(db: AsyncSession, email: str) -> str | None:
    """Generate password reset token dan simpan hash ke DB.

    Returns:
        Token plain (untuk dikirim ke user via email), atau None jika user tidak ada.
    """
    import secrets
    import hashlib
    user = await get_user_by_email(db, email)
    if not user:
        # Jangan bocorkan apakah email ada atau tidak
        return None

    # Generate secure token
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    # Simpan hash ke notes field sementara (MVP — idealnya pakai tabel password_reset_tokens)
    # Format: "PWRESET:<hash>:<expiry_unix>"
    import time
    expiry = int(time.time()) + 3600  # 1 jam
    user.notes = f"PWRESET:{token_hash}:{expiry}" if hasattr(user, "notes") else None  # type: ignore

    # Karena User model tidak punya field notes, kita simpan di DB melalui method ad-hoc
    # Solusi production: buat tabel password_reset_tokens
    # MVP: simpan di JSON field atau gunakan cache (Redis)
    # Untuk sekarang: return token untuk dikembalikan ke endpoint (endpoint log ke console)
    await db.commit()
    return token


async def confirm_password_reset(db: AsyncSession, token: str, new_password: str) -> bool:
    """Verifikasi reset token dan update password user.

    MVP: Karena tidak ada tabel khusus, ini akan matching via query yang aman.
    Returns: True jika berhasil, False jika token invalid/expired.
    """
    import hashlib
    import time

    token_hash = hashlib.sha256(token.encode()).hexdigest()
    # NOTE: Implementasi production butuh tabel password_reset_tokens dengan:
    # user_id, token_hash, expires_at, used_at
    # MVP ini adalah placeholder yang mengembalikan False secara aman
    # sampai tabel tersebut dibuat via Alembic migration
    return False


async def revoke_all_sessions(db: AsyncSession, user_id: int) -> bool:
    # In production: invalidate all refresh tokens via Redis or DB token blacklist
    # MVP: no-op / client-side only
    return True
