"""Interview business logic."""
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.interviews.repositories.repository import (
    get_application_for_company,
    get_interview_by_application_id,
    save_interview,
)
from app.features.interviews.schemas.schema import (
    InterviewDetailResponse,
    InterviewScheduledResponse,
    ScheduleInterviewRequest,
)
from app.features.models import Interview, User


async def schedule_interview(
    db: AsyncSession,
    *,
    current_user: User,
    data: ScheduleInterviewRequest,
) -> InterviewScheduledResponse:
    application = await get_application_for_company(
        db,
        application_id=data.application_id,
        company_id=current_user.company_id,
    )
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    interview = Interview(
        application_id=data.application_id,
        scheduled_at=data.scheduled_at,
        duration_minutes=data.duration_minutes,
        location=data.location,
        meeting_link=data.meeting_link,
        interview_type=data.interview_type,
        interviewer_ids=data.interviewer_ids or [],
    )
    interview = await save_interview(db, interview)
    await db.commit()
    return InterviewScheduledResponse(
        interview_id=interview.id,
        scheduled_at=data.scheduled_at.isoformat(),
    )


async def get_interview(db: AsyncSession, application_id: int) -> InterviewDetailResponse:
    interview = await get_interview_by_application_id(db, application_id)
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    return InterviewDetailResponse(
        id=interview.id,
        scheduled_at=interview.scheduled_at.isoformat() if interview.scheduled_at else None,
        duration=interview.duration_minutes,
        location=interview.location,
        meeting_link=interview.meeting_link,
        result=interview.result,
    )
