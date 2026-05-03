"""User data access helpers."""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils.pagination import PaginationParams
from app.features.models import User
from app.shared.enums.user_roles import UserRole


async def save_user(db: AsyncSession, user: User) -> User:
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def list_users(
    db: AsyncSession,
    *,
    pagination: PaginationParams,
    current_user_role: UserRole,
    current_user_company_id: int | None,
    company_id: int | None = None,
    role: UserRole | None = None,
    q: str | None = None,
) -> tuple[list[User], int]:
    stmt = select(User).where(User.deleted_at.is_(None))

    if current_user_role == UserRole.HR:
        stmt = stmt.where(User.company_id == current_user_company_id)
    elif company_id is not None and current_user_role == UserRole.SUPER_ADMIN:
        stmt = stmt.where(User.company_id == company_id)

    if role:
        stmt = stmt.where(User.role == role)
    if q:
        stmt = stmt.where(User.full_name.ilike(f"%{q}%"))

    total_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_result.scalar_one()

    result = await db.execute(stmt.offset(pagination.offset).limit(pagination.limit))
    return list(result.scalars().all()), total
