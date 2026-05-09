"""User management API."""
from typing import Optional
from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.base import get_db
from app.features.auth.dependencies.auth import require_super_admin, get_current_user
from app.features.users.schemas.schema import CreateHRAccountRequest, UserCreatedResponse, UserListItem, UpdateUserRequest
from app.features.users.services.service import create_hr_account as create_hr_account_service, get_users_stats as get_users_stats_service, update_user as update_user_service, delete_user as delete_user_service, get_user as get_user_service
from app.features.users.services.service import list_users as list_users_service
from app.shared.schemas.response import StandardResponse, PaginatedResponse
from app.core.utils.pagination import PaginationParams
from app.shared.enums.user_roles import UserRole

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/stats", response_model=StandardResponse[dict])
async def get_users_stats(
    db: AsyncSession = Depends(get_db),
    _=Depends(require_super_admin),
):
    stats = await get_users_stats_service(db)
    return StandardResponse.ok(data=stats)


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
    status: Optional[str] = None,
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
        status=status,
        q=q,
    )
    return StandardResponse.ok(data=users)


@router.get("/{user_id}", response_model=StandardResponse[UserListItem])
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_super_admin),
):
    user = await get_user_service(db, user_id)
    return StandardResponse.ok(data=user)


@router.patch("/{user_id}", response_model=StandardResponse[UserListItem])
async def update_user(
    user_id: int,
    data: UpdateUserRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_super_admin),
):
    user = await update_user_service(db, user_id, data)
    return StandardResponse.ok(data=user, message="User updated successfully")


@router.delete("/{user_id}", response_model=StandardResponse[dict])
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_super_admin),
):
    await delete_user_service(db, user_id)
    return StandardResponse.ok(data={"id": user_id}, message="User deleted successfully")


@router.post("/upload-avatar", response_model=StandardResponse[dict])
async def upload_user_avatar(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_super_admin),
):
    """Upload user avatar to Cloudflare R2."""
    from app.features.companies.services.service import upload_logo as upload_to_r2
    url = await upload_to_r2(db, file)
    return StandardResponse.ok(data={"avatar_url": url})
