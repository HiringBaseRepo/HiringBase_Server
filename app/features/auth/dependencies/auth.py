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
from app.shared.helpers.localization import get_label
from app.shared.constants.errors import (
    ERR_INVALID_TOKEN,
    ERR_SESSION_EXPIRED,
    ERR_UNAUTHORIZED,
)

security = HTTPBearer(auto_error=False)


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> User:
    if not credentials:
        raise UnauthenticatedException()

    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise UnauthenticatedException(get_label(ERR_INVALID_TOKEN))

    user_id = int(payload.get("sub"))
    user = await get_user_by_id(db, user_id)

    if not user:
        raise UnauthenticatedException()
    if not user.is_active:
        raise UserInactiveException()
        
    token_version = payload.get("token_version")
    if token_version is None or token_version != user.token_version:
        raise UnauthenticatedException(get_label(ERR_SESSION_EXPIRED))

    return user


def require_role(*roles: UserRole):
    async def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            # Note: We keep the roles list dynamic in the message but use localization for the prefix
            role_names = ", ".join([get_label(r) for r in roles])
            raise UnauthorizedException(
                f"{get_label(ERR_UNAUTHORIZED)}. Memerlukan peran: {role_names}"
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
