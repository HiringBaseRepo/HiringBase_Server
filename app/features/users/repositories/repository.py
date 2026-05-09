"""User data access helpers."""
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils.pagination import PaginationParams
from app.features.users.models import User
from app.shared.enums.user_roles import UserRole


async def save_user(db: AsyncSession, user: User) -> User:
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def update_user_repo(db: AsyncSession, user: User) -> User:
    await db.flush()
    await db.refresh(user)
    return user


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id, User.deleted_at.is_(None)))
    return result.scalar_one_or_none()


async def delete_user(db: AsyncSession, user: User) -> None:
    from datetime import datetime, timezone
    user.deleted_at = datetime.now(timezone.utc)
    user.is_active = False
    await db.flush()


async def list_users(
    db: AsyncSession,
    *,
    pagination: PaginationParams,
    current_user_role: UserRole,
    current_user_company_id: int | None,
    company_id: int | None = None,
    role: UserRole | None = None,
    status: str | None = None,
    q: str | None = None,
) -> tuple[list[User], int]:
    stmt = select(User).options(selectinload(User.company))

    if current_user_role == UserRole.HR:
        stmt = stmt.where(User.company_id == current_user_company_id)
    elif company_id is not None and current_user_role == UserRole.SUPER_ADMIN:
        stmt = stmt.where(User.company_id == company_id)

    # Filter out deleted users unless explicitly requesting archived
    if status != "archived":
        stmt = stmt.where(User.deleted_at.is_(None))

    if role:
        stmt = stmt.where(User.role == role)
    if status:
        if status == "active":
            stmt = stmt.where(User.is_active.is_(True))
        elif status == "inactive":
            stmt = stmt.where(User.is_active.is_(False))
        elif status == "archived":
            stmt = stmt.where(User.deleted_at.is_not(None))
            # Note: The initial query filters out deleted_at.is_(None), 
            # so we need to adjust the base query if archived is needed.
            # For now, let's just handle active/inactive.
    if q:
        stmt = stmt.where(User.full_name.ilike(f"%{q}%"))

    total_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_result.scalar_one()

    result = await db.execute(stmt.offset(pagination.offset).limit(pagination.limit))
    return list(result.scalars().all()), total


async def get_users_stats(db: AsyncSession) -> dict:
    """Get aggregated user statistics."""
    total = await db.execute(select(func.count(User.id)).where(User.deleted_at.is_(None)))
    active = await db.execute(
        select(func.count(User.id)).where(User.is_active.is_(True), User.deleted_at.is_(None))
    )
    hr_role = await db.execute(
        select(func.count(User.id)).where(User.role == UserRole.HR, User.deleted_at.is_(None))
    )
    
    from app.features.companies.models import Company
    companies = await db.execute(select(func.count(Company.id)).where(Company.deleted_at.is_(None)))

    return {
        "total_users": total.scalar_one(),
        "active_users": active.scalar_one(),
        "hr_accounts": hr_role.scalar_one(),
        "total_companies": companies.scalar_one(),
    }
