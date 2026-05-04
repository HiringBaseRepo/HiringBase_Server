"""Company data access helpers."""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils.pagination import PaginationParams
from app.features.companies.models import Company
from app.features.jobs.models import Job
from app.features.users.models import User
from app.features.applications.models import Application
from app.shared.enums.application_status import ApplicationStatus
from app.shared.enums.job_status import JobStatus
from app.shared.enums.user_roles import UserRole


async def save_company(db: AsyncSession, company: Company) -> Company:
    db.add(company)
    await db.flush()
    await db.refresh(company)
    return company


async def get_company_by_id(db: AsyncSession, company_id: int) -> Company | None:
    result = await db.execute(select(Company).where(Company.id == company_id))
    return result.scalar_one_or_none()


async def list_companies(
    db: AsyncSession,
    *,
    pagination: PaginationParams,
    q: str | None = None,
    is_active: bool | None = None,
) -> tuple[list[Company], int]:
    stmt = select(Company).where(Company.deleted_at.is_(None))
    if q:
        stmt = stmt.where(Company.name.ilike(f"%{q}%"))
    if is_active is not None:
        stmt = stmt.where(Company.is_active == is_active)

    total_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_result.scalar_one()
    result = await db.execute(stmt.offset(pagination.offset).limit(pagination.limit))
    return list(result.scalars().all()), total


async def count_jobs(db: AsyncSession, company_id: int | None = None, published_only: bool = False) -> int:
    stmt = select(func.count(Job.id)).where(Job.deleted_at.is_(None))
    if company_id is not None:
        stmt = stmt.where(Job.company_id == company_id)
    if published_only:
        stmt = stmt.where(Job.status == JobStatus.PUBLISHED)
    result = await db.execute(stmt)
    return result.scalar_one()


async def count_applications(
    db: AsyncSession,
    *,
    company_id: int | None = None,
    status: ApplicationStatus | None = None,
) -> int:
    stmt = select(func.count(Application.id)).where(Application.deleted_at.is_(None))
    if company_id is not None:
        stmt = stmt.where(Application.job_id.in_(select(Job.id).where(Job.company_id == company_id)))
    if status is not None:
        stmt = stmt.where(Application.status == status)
    result = await db.execute(stmt)
    return result.scalar_one()


async def count_hr_users(db: AsyncSession, company_id: int) -> int:
    result = await db.execute(
        select(func.count(User.id)).where(
            User.company_id == company_id,
            User.role == UserRole.HR,
            User.deleted_at.is_(None),
        )
    )
    return result.scalar_one()


async def list_all_companies(db: AsyncSession) -> list[Company]:
    result = await db.execute(
        select(Company).where(Company.deleted_at.is_(None)).order_by(Company.created_at.desc())
    )
    return list(result.scalars().all())
