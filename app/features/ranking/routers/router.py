"""Ranking API."""
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.base import get_db
from app.features.auth.dependencies.auth import require_hr
from app.features.ranking.schemas.schema import RankingItem
from app.features.ranking.services.service import rank_applicants as rank_applicants_service
from app.shared.schemas.response import StandardResponse, PaginatedResponse
from app.core.utils.pagination import PaginationParams
from app.shared.enums.application_status import ApplicationStatus

router = APIRouter(prefix="/ranking", tags=["Ranking"])


@router.get("/jobs/{job_id}", response_model=StandardResponse[PaginatedResponse[RankingItem]])
async def rank_applicants(
    job_id: int,
    status: Optional[ApplicationStatus] = None,
    min_score: Optional[float] = None,
    top_n: Optional[int] = None,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_hr),
):
    result = await rank_applicants_service(
        db,
        current_user=current_user,
        job_id=job_id,
        pagination=pagination,
        status_filter=status,
        min_score=min_score,
        top_n=top_n,
    )
    return StandardResponse.ok(data=result)
