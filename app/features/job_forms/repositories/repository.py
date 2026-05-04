"""Job form data access helpers."""
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.jobs.models import JobFormField


async def save_form_field(db: AsyncSession, field: JobFormField) -> JobFormField:
    db.add(field)
    await db.flush()
    await db.refresh(field)
    return field


async def get_form_field(db: AsyncSession, *, job_id: int, field_id: int) -> JobFormField | None:
    result = await db.execute(
        select(JobFormField).where(JobFormField.id == field_id, JobFormField.job_id == job_id)
    )
    return result.scalar_one_or_none()


async def delete_form_field(db: AsyncSession, field: JobFormField) -> None:
    await db.delete(field)
    await db.flush()


async def update_field_order(db: AsyncSession, *, job_id: int, field_id: int, order_index: int) -> None:
    await db.execute(
        update(JobFormField)
        .where(JobFormField.id == field_id, JobFormField.job_id == job_id)
        .values(order_index=order_index)
    )
