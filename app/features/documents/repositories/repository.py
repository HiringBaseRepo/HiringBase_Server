"""Document data access helpers."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.models import Application, ApplicationDocument, Job


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


async def save_document(db: AsyncSession, document: ApplicationDocument) -> ApplicationDocument:
    db.add(document)
    await db.flush()
    await db.refresh(document)
    return document
