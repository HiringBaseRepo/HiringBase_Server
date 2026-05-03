"""Ticket data access helpers."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.models import Application, Job, Ticket, User


async def get_ticket_by_code(db: AsyncSession, ticket_code: str) -> Ticket | None:
    result = await db.execute(select(Ticket).where(Ticket.code == ticket_code))
    return result.scalar_one_or_none()


async def get_application_by_id(db: AsyncSession, application_id: int) -> Application | None:
    result = await db.execute(select(Application).where(Application.id == application_id))
    return result.scalar_one_or_none()


async def get_job_by_id(db: AsyncSession, job_id: int) -> Job | None:
    result = await db.execute(select(Job).where(Job.id == job_id))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
