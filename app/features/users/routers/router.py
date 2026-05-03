"""User management API."""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database.base import get_db
from app.features.auth.dependencies.auth import require_super_admin, require_hr, get_current_user
from app.features.models import User, Company
from app.shared.schemas.response import StandardResponse, PaginatedResponse
from app.core.utils.pagination import PaginationParams
from app.shared.enums.user_roles import UserRole

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/hr", response_model=StandardResponse[dict])
async def create_hr_account(
    email: str,
    password: str,
    full_name: str,
    company_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_super_admin),
):
    from app.core.security.hashing import get_password_hash
    user = User(
        email=email,
        password_hash=get_password_hash(password),
        full_name=full_name,
        company_id=company_id,
        role=UserRole.HR,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return StandardResponse.ok(data={
        "id": user.id, "email": user.email, "full_name": user.full_name,
        "role": user.role.value, "company_id": user.company_id,
    })


@router.get("", response_model=StandardResponse[PaginatedResponse[dict]])
async def list_users(
    company_id: Optional[int] = None,
    role: Optional[UserRole] = None,
    q: Optional[str] = None,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    stmt = select(User).where(User.deleted_at.is_(None))
    if current_user.role == UserRole.HR:
        stmt = stmt.where(User.company_id == current_user.company_id)
    if company_id is not None and current_user.role == UserRole.SUPER_ADMIN:
        stmt = stmt.where(User.company_id == company_id)
    if role:
        stmt = stmt.where(User.role == role)
    if q:
        stmt = stmt.where(User.full_name.ilike(f"%{q}%"))

    total_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_result.scalar_one()

    stmt = stmt.offset(pagination.offset).limit(pagination.limit)
    result = await db.execute(stmt)
    items = []
    for u in result.scalars().all():
        items.append({
            "id": u.id, "email": u.email, "full_name": u.full_name,
            "role": u.role.value, "company_id": u.company_id, "is_active": u.is_active,
        })

    pages = (total + pagination.per_page - 1) // pagination.per_page
    return StandardResponse.ok(data=PaginatedResponse(
        data=items, total=total, page=pagination.page,
        per_page=pagination.per_page, total_pages=pages,
        has_next=pagination.page < pages, has_prev=pagination.page > 1,
    ))
