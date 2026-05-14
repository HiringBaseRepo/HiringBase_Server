"""Auth dependencies for FastAPI routes."""
from typing import Annotated, Optional

from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.base import get_db
from app.core.security.jwt import decode_token
from app.core.exceptions import (
    UnauthenticatedException,
    UnauthorizedException,
    UserInactiveException,
)
from app.features.auth.repositories.repository import get_user_by_id
from app.features.users.models import User
from app.shared.enums.user_roles import UserRole

security = HTTPBearer(auto_error=False)


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> User:
    if not credentials:
        raise UnauthenticatedException()

    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise UnauthenticatedException("Token tidak valid atau kedaluwarsa")

    user_id = int(payload.get("sub"))
    user = await get_user_by_id(db, user_id)

    if not user:
        raise UnauthenticatedException()
    if not user.is_active:
        raise UserInactiveException()
        
    token_version = payload.get("token_version")
    if token_version is None or token_version != user.token_version:
        raise UnauthenticatedException("Sesi telah berakhir, silakan login kembali")

    return user


def require_role(*roles: UserRole):
    async def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise UnauthorizedException(
                f"Akses ditolak. Memerlukan peran: {[r.value for r in roles]}"
            )
        return user
    return role_checker


require_super_admin = require_role(UserRole.SUPER_ADMIN)
require_hr = require_role(UserRole.HR, UserRole.SUPER_ADMIN)
require_applicant = require_role(UserRole.APPLICANT, UserRole.HR, UserRole.SUPER_ADMIN)

# Shared router dependency aliases (AGENTS.md convention)
DbDep = Annotated[AsyncSession, Depends(get_db)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]
HrUserDep = Annotated[User, Depends(require_hr)]
SuperAdminDep = Annotated[User, Depends(require_super_admin)]
