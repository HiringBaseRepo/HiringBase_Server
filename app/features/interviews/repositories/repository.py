"""Interview data access helpers."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.applications.models import Application
from app.features.interviews.models import Interview
from app.features.jobs.models import Job


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


async def save_interview(db: AsyncSession, interview: Interview) -> Interview:
    db.add(interview)
    await db.flush()
    await db.refresh(interview)
    return interview


async def get_interview_by_application_id(db: AsyncSession, application_id: int) -> Interview | None:
    result = await db.execute(select(Interview).where(Interview.application_id == application_id))
    return result.scalar_one_or_none()
