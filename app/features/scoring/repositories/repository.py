"""Scoring template data access helpers."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.models import JobScoringTemplate


async def get_template_by_job_id(db: AsyncSession, job_id: int) -> JobScoringTemplate | None:
    result = await db.execute(select(JobScoringTemplate).where(JobScoringTemplate.job_id == job_id))
    return result.scalar_one_or_none()


async def get_template_by_id(db: AsyncSession, template_id: int) -> JobScoringTemplate | None:
    result = await db.execute(select(JobScoringTemplate).where(JobScoringTemplate.id == template_id))
    return result.scalar_one_or_none()


async def delete_template(db: AsyncSession, template: JobScoringTemplate) -> None:
    await db.delete(template)
    await db.flush()


async def save_template(db: AsyncSession, template: JobScoringTemplate) -> JobScoringTemplate:
    db.add(template)
    await db.flush()
    await db.refresh(template)
    return template
