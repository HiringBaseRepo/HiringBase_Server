"""Ranking business logic."""
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils.pagination import PaginationParams
from app.features.users.models import User
from app.features.ranking.repositories.repository import (
    get_job_for_company,
    get_user_by_id,
    list_ranked_applications,
)
from app.features.ranking.schemas.schema import RankingItem
from app.shared.enums.application_status import ApplicationStatus
from app.shared.schemas.response import PaginatedResponse


async def rank_applicants(
    db: AsyncSession,
    *,
    current_user: User,
    job_id: int,
    pagination: PaginationParams,
    status_filter: ApplicationStatus | None = None,
    min_score: float | None = None,
    top_n: int | None = None,
) -> PaginatedResponse[RankingItem]:
    job = await get_job_for_company(db, job_id=job_id, company_id=current_user.company_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    rows, total = await list_ranked_applications(
        db,
        job_id=job_id,
        pagination=pagination,
        status=status_filter,
        min_score=min_score,
        top_n=top_n,
    )
    items = []
    for application, score in rows:
        applicant = await get_user_by_id(db, application.applicant_id)
        items.append(
            RankingItem(
                application_id=application.id,
                applicant_name=applicant.full_name if applicant else None,
                applicant_email=applicant.email if applicant else None,
                status=application.status.value,
                final_score=round(score.final_score, 2) if score else None,
                skill_match=round(score.skill_match_score, 2) if score else None,
                experience=round(score.experience_score, 2) if score else None,
                education=round(score.education_score, 2) if score else None,
                portfolio=round(score.portfolio_score, 2) if score else None,
                risk_level=score.risk_level if score else None,
                created_at=application.created_at.isoformat() if application.created_at else None,
            )
        )
    pages = (total + pagination.per_page - 1) // pagination.per_page
    return PaginatedResponse(
        data=items,
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
        total_pages=pages,
        has_next=pagination.page < pages,
        has_prev=pagination.page > 1,
    )
