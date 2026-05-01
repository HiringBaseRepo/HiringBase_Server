"""Ranking API."""
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database.base import get_db
from app.features.auth.dependencies import require_hr
from app.features.models import Application, CandidateScore, Job, User
from app.shared.schemas.response import StandardResponse, PaginatedResponse
from app.core.utils.pagination import PaginationParams
from app.shared.enums.application_status import ApplicationStatus

router = APIRouter(prefix="/ranking", tags=["Ranking"])


@router.get("/jobs/{job_id}", response_model=StandardResponse[PaginatedResponse[dict]])
async def rank_applicants(
    job_id: int,
    status: Optional[ApplicationStatus] = None,
    min_score: Optional[float] = None,
    top_n: Optional[int] = None,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_hr),
):
    # Verify job belongs to company
    job_result = await db.execute(select(Job).where(Job.id == job_id, Job.company_id == current_user.company_id))
    job = job_result.scalar_one_or_none()
    if not job:
        return StandardResponse.error(message="Job not found", status_code=404)

    stmt = select(Application, CandidateScore).join(
        CandidateScore, Application.id == CandidateScore.application_id, isouter=True
    ).where(
        Application.job_id == job_id,
        Application.deleted_at.is_(None),
    ).order_by(CandidateScore.final_score.desc().nullslast(), Application.created_at.desc())

    if status:
        stmt = stmt.where(Application.status == status)
    if min_score is not None:
        stmt = stmt.where(CandidateScore.final_score >= min_score)

    total_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_result.scalar_one()

    limit = top_n if top_n else pagination.limit
    offset = pagination.offset if not top_n else 0

    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)

    items = []
    for app, score in result.all():
        applicant = await db.execute(select(User).where(User.id == app.applicant_id))
        user = applicant.scalar_one_or_none()
        items.append({
            "application_id": app.id,
            "applicant_name": user.full_name if user else None,
            "applicant_email": user.email if user else None,
            "status": app.status.value,
            "final_score": round(score.final_score, 2) if score else None,
            "skill_match": round(score.skill_match_score, 2) if score else None,
            "experience": round(score.experience_score, 2) if score else None,
            "education": round(score.education_score, 2) if score else None,
            "portfolio": round(score.portfolio_score, 2) if score else None,
            "risk_level": score.risk_level if score else None,
            "created_at": app.created_at.isoformat() if app.created_at else None,
        })

    pages = (total + pagination.per_page - 1) // pagination.per_page
    return StandardResponse.ok(data=PaginatedResponse(
        data=items, total=total, page=pagination.page,
        per_page=pagination.per_page, total_pages=pages,
        has_next=pagination.page < pages, has_prev=pagination.page > 1,
    ))
