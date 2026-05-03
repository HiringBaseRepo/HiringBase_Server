"""User management API."""
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.base import get_db
from app.features.auth.dependencies.auth import require_super_admin, get_current_user
from app.features.users.schemas.schema import CreateHRAccountRequest, UserCreatedResponse, UserListItem
from app.features.users.services.service import create_hr_account as create_hr_account_service
from app.features.users.services.service import list_users as list_users_service
from app.shared.schemas.response import StandardResponse, PaginatedResponse
from app.core.utils.pagination import PaginationParams
from app.shared.enums.user_roles import UserRole

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/hr", response_model=StandardResponse[UserCreatedResponse])
async def create_hr_account(
    data: CreateHRAccountRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_super_admin),
):
    user = await create_hr_account_service(db, data)
    return StandardResponse.ok(data=user)


@router.get("", response_model=StandardResponse[PaginatedResponse[UserListItem]])
async def list_users(
    company_id: Optional[int] = None,
    role: Optional[UserRole] = None,
    q: Optional[str] = None,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    users = await list_users_service(
        db,
        current_user=current_user,
        pagination=pagination,
        company_id=company_id,
        role=role,
        q=q,
    )
    return StandardResponse.ok(data=users)
