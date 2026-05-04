"""Ranking data access helpers."""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils.pagination import PaginationParams
from app.features.applications.models import Application
from app.features.screening.models import CandidateScore
from app.features.jobs.models import Job
from app.features.users.models import User
from app.shared.enums.application_status import ApplicationStatus


async def get_job_for_company(db: AsyncSession, *, job_id: int, company_id: int | None) -> Job | None:
    result = await db.execute(select(Job).where(Job.id == job_id, Job.company_id == company_id))
    return result.scalar_one_or_none()


async def list_ranked_applications(
    db: AsyncSession,
    *,
    job_id: int,
    pagination: PaginationParams,
    status: ApplicationStatus | None = None,
    min_score: float | None = None,
    top_n: int | None = None,
) -> tuple[list[tuple[Application, CandidateScore | None]], int]:
    stmt = (
        select(Application, CandidateScore)
        .join(CandidateScore, Application.id == CandidateScore.application_id, isouter=True)
        .where(Application.job_id == job_id, Application.deleted_at.is_(None))
        .order_by(CandidateScore.final_score.desc().nullslast(), Application.created_at.desc())
    )
    if status:
        stmt = stmt.where(Application.status == status)
    if min_score is not None:
        stmt = stmt.where(CandidateScore.final_score >= min_score)

    total_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_result.scalar_one()
    limit = top_n if top_n else pagination.limit
    offset = pagination.offset if not top_n else 0
    result = await db.execute(stmt.offset(offset).limit(limit))
    return list(result.all()), total


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
