"""Application data access helpers."""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.core.utils.pagination import PaginationParams
from app.features.applications.models import (
    Application,
    ApplicationAnswer,
    ApplicationDocument,
    ApplicationStatusLog,
)
from app.features.companies.models import Company
from app.features.jobs.models import Job, JobFormField, JobKnockoutRule
from app.features.tickets.models import Ticket
from app.features.users.models import User
from app.shared.enums.application_status import ApplicationStatus
from app.shared.enums.job_status import JobStatus


async def list_public_jobs(
    db: AsyncSession,
    *,
    pagination: PaginationParams,
    q: str | None = None,
    location: str | None = None,
) -> tuple[list[Job], int]:
    stmt = select(Job).where(
        Job.status == JobStatus.PUBLISHED,
        Job.is_public == True,
        Job.deleted_at.is_(None),
    )
    if q:
        stmt = stmt.where(Job.title.ilike(f"%{q}%"))
    if location:
        stmt = stmt.where(Job.location.ilike(f"%{location}%"))
    total_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_result.scalar_one()
    result = await db.execute(
        stmt.order_by(Job.published_at.desc()).offset(pagination.offset).limit(pagination.limit)
    )
    return list(result.scalars().all()), total


async def get_company_by_id(db: AsyncSession, company_id: int) -> Company | None:
    result = await db.execute(select(Company).where(Company.id == company_id))
    return result.scalar_one_or_none()


async def get_public_job_by_id(db: AsyncSession, job_id: int) -> Job | None:
    result = await db.execute(
        select(Job).where(
            Job.id == job_id,
            Job.status == JobStatus.PUBLISHED,
            Job.is_public == True,
            Job.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def get_published_job_by_id(db: AsyncSession, job_id: int) -> Job | None:
    result = await db.execute(
        select(Job).where(Job.id == job_id, Job.status == JobStatus.PUBLISHED, Job.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def get_form_fields_by_job_id(db: AsyncSession, job_id: int) -> list[JobFormField]:
    result = await db.execute(
        select(JobFormField).where(JobFormField.job_id == job_id).order_by(JobFormField.order_index)
    )
    return list(result.scalars().all())


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_application_by_job_and_applicant(
    db: AsyncSession,
    *,
    job_id: int,
    applicant_id: int,
) -> Application | None:
    result = await db.execute(
        select(Application).where(
            Application.job_id == job_id,
            Application.applicant_id == applicant_id,
            Application.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def get_form_field_by_key(db: AsyncSession, *, job_id: int, field_key: str) -> JobFormField | None:
    result = await db.execute(
        select(JobFormField).where(JobFormField.job_id == job_id, JobFormField.field_key == field_key)
    )
    return result.scalar_one_or_none()


async def get_knockout_rules_by_job_id(db: AsyncSession, job_id: int) -> list[JobKnockoutRule]:
    result = await db.execute(
        select(JobKnockoutRule).where(
            JobKnockoutRule.job_id == job_id,
            JobKnockoutRule.is_active == True,
        ).order_by(JobKnockoutRule.order_index)
    )
    return list(result.scalars().all())


async def save_user(db: AsyncSession, user: User) -> User:
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def save_application(db: AsyncSession, application: Application) -> Application:
    db.add(application)
    await db.flush()
    await db.refresh(application)
    return application


async def add_answer(db: AsyncSession, answer: ApplicationAnswer) -> None:
    db.add(answer)
    await db.flush()


async def add_document(db: AsyncSession, document: ApplicationDocument) -> None:
    db.add(document)
    await db.flush()


async def save_ticket(db: AsyncSession, ticket: Ticket) -> Ticket:
    db.add(ticket)
    await db.flush()
    await db.refresh(ticket)
    return ticket


async def add_status_log(db: AsyncSession, log: ApplicationStatusLog) -> None:
    db.add(log)


async def list_applications(
    db: AsyncSession,
    *,
    company_id: int | None,
    pagination: PaginationParams,
    job_id: int | None = None,
    status: ApplicationStatus | None = None,
    q: str | None = None,
) -> tuple[list[Application], int]:
    stmt = select(Application).join(Job).where(
        Job.company_id == company_id,
        Application.deleted_at.is_(None),
    )
    if job_id:
        stmt = stmt.where(Application.job_id == job_id)
    if status:
        stmt = stmt.where(Application.status == status)
    if q:
        stmt = stmt.join(User).where(User.full_name.ilike(f"%{q}%"))

    total_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_result.scalar_one()
    result = await db.execute(
        stmt.order_by(Application.created_at.desc()).offset(pagination.offset).limit(pagination.limit)
    )
    return list(result.scalars().all()), total


async def get_application_for_company(
    db: AsyncSession,
    *,
    application_id: int,
    company_id: int | None,
) -> Application | None:
    result = await db.execute(
        select(Application).join(Job).where(
            Application.id == application_id,
            Job.company_id == company_id,
        )
    )
    return result.scalar_one_or_none()


async def update_application_status(
    db: AsyncSession, application: Application, new_status: ApplicationStatus
) -> Application:
    application.status = new_status
    await db.flush()
    return application


async def get_application_detail(
    db: AsyncSession, *, application_id: int, company_id: int | None
) -> Application | None:
    stmt = (
        select(Application)
        .options(
            joinedload(Application.applicant),
            joinedload(Application.job),
            selectinload(Application.answers).joinedload(ApplicationAnswer.form_field),
            selectinload(Application.documents),
            selectinload(Application.scores),
        )
        .join(Job)
        .where(
            Application.id == application_id,
            Job.company_id == company_id,
            Application.deleted_at.is_(None),
        )
    )
    result = await db.execute(stmt)
    return result.unique().scalar_one_or_none()
