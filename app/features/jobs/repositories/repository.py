"""Job data access helpers."""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils.pagination import PaginationParams
from app.features.models import Job, JobFormField, JobKnockoutRule, JobRequirement
from app.shared.enums.job_status import JobStatus


async def save_job(db: AsyncSession, job: Job) -> Job:
    db.add(job)
    await db.flush()
    await db.refresh(job)
    return job


async def save_requirements(db: AsyncSession, requirements: list[JobRequirement]) -> None:
    for requirement in requirements:
        db.add(requirement)
    await db.flush()


async def save_form_fields(db: AsyncSession, fields: list[JobFormField]) -> None:
    for field in fields:
        db.add(field)
    await db.flush()


async def get_job_for_company(db: AsyncSession, job_id: int, company_id: int | None) -> Job | None:
    result = await db.execute(
        select(Job).where(Job.id == job_id, Job.company_id == company_id)
    )
    return result.scalar_one_or_none()


async def list_jobs(
    db: AsyncSession,
    *,
    company_id: int | None,
    pagination: PaginationParams,
    status: JobStatus | None = None,
    q: str | None = None,
) -> tuple[list[Job], int]:
    stmt = select(Job).where(Job.company_id == company_id, Job.deleted_at.is_(None))
    if status:
        stmt = stmt.where(Job.status == status)
    if q:
        stmt = stmt.where(Job.title.ilike(f"%{q}%"))

    total_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_result.scalar_one()

    result = await db.execute(
        stmt.order_by(Job.created_at.desc()).offset(pagination.offset).limit(pagination.limit)
    )
    return list(result.scalars().all()), total


async def get_requirements_by_job_id(db: AsyncSession, job_id: int) -> list[JobRequirement]:
    result = await db.execute(select(JobRequirement).where(JobRequirement.job_id == job_id))
    return list(result.scalars().all())


async def get_form_fields_by_job_id(db: AsyncSession, job_id: int) -> list[JobFormField]:
    result = await db.execute(
        select(JobFormField).where(JobFormField.job_id == job_id).order_by(JobFormField.order_index)
    )
    return list(result.scalars().all())


async def get_knockout_rules_by_job_id(db: AsyncSession, job_id: int) -> list[JobKnockoutRule]:
    result = await db.execute(select(JobKnockoutRule).where(JobKnockoutRule.job_id == job_id))
    return list(result.scalars().all())
