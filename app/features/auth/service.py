"""Auth business logic."""
from typing import Optional, Tuple
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.hashing import verify_password, get_password_hash
from app.core.security.jwt import create_access_token, create_refresh_token, decode_token
from app.core.utils.ticket import generate_apply_code
from app.features.models import User, Company
from app.features.auth.schemas import RegisterRequest, TokenPair
from app.shared.enums.user_roles import UserRole
from app.shared.constants.errors import ERR_INVALID_CREDENTIALS, ERR_USER_NOT_FOUND


async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email, User.deleted_at.is_(None)))
    user = result.scalar_one_or_none()
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
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def create_company_and_hr(db: AsyncSession, data: RegisterRequest) -> Tuple[User, Company]:
    company = Company(
        name=data.company_name or data.full_name + " Company",
        slug=generate_apply_code().replace("FRM-", "").lower(),
    )
    db.add(company)
    await db.flush()
    await db.refresh(company)

    hr = User(
        email=data.email,
        password_hash=get_password_hash(data.password),
        full_name=data.full_name,
        phone=data.phone,
        role=UserRole.HR,
        company_id=company.id,
    )
    db.add(hr)
    await db.flush()
    await db.refresh(hr)
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
    result = await db.execute(select(User).where(User.id == user_id, User.deleted_at.is_(None)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        return None
    return await generate_token_pair(user)


async def revoke_all_sessions(db: AsyncSession, user_id: int) -> bool:
    # In production: invalidate all refresh tokens via Redis or DB token blacklist
    # MVP: no-op / client-side only
    return True
