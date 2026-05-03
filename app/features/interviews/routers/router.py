"""Interview Scheduler API."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.base import get_db
from app.features.auth.dependencies.auth import require_hr
from app.features.interviews.schemas.schema import (
    InterviewDetailResponse,
    InterviewScheduledResponse,
    ScheduleInterviewRequest,
)
from app.features.interviews.services.service import (
    get_interview as get_interview_service,
    schedule_interview as schedule_interview_service,
)
from app.shared.schemas.response import StandardResponse

router = APIRouter(prefix="/interviews", tags=["Interviews"])


@router.post("", response_model=StandardResponse[InterviewScheduledResponse])
async def schedule_interview(
    data: ScheduleInterviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_hr),
):
    result = await schedule_interview_service(db, current_user=current_user, data=data)
    return StandardResponse.ok(data=result)


@router.get("/application/{application_id}", response_model=StandardResponse[InterviewDetailResponse])
async def get_interview(application_id: int, db: AsyncSession = Depends(get_db), current_user=Depends(require_hr)):
    result = await get_interview_service(db, application_id)
    return StandardResponse.ok(data=result)
