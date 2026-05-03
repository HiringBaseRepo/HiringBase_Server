"""Interview Scheduler API."""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database.base import get_db
from app.features.auth.dependencies.auth import require_hr
from app.features.models import Interview, Application, Job
from app.shared.schemas.response import StandardResponse

router = APIRouter(prefix="/interviews", tags=["Interviews"])


@router.post("", response_model=StandardResponse[dict])
async def schedule_interview(
    application_id: int,
    scheduled_at: datetime,
    duration_minutes: int = 60,
    location: Optional[str] = None,
    meeting_link: Optional[str] = None,
    interview_type: str = "in_person",
    interviewer_ids: Optional[list] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_hr),
):
    result = await db.execute(select(Application).join(Job).where(
        Application.id == application_id,
        Job.company_id == current_user.company_id,
    ))
    application = result.scalar_one_or_none()
    if not application:
        return StandardResponse.error(message="Application not found", status_code=404)

    interview = Interview(
        application_id=application_id,
        scheduled_at=scheduled_at,
        duration_minutes=duration_minutes,
        location=location,
        meeting_link=meeting_link,
        interview_type=interview_type,
        interviewer_ids=interviewer_ids or [],
    )
    db.add(interview)
    await db.commit()
    await db.refresh(interview)
    return StandardResponse.ok(data={"interview_id": interview.id, "scheduled_at": scheduled_at.isoformat()})


@router.get("/application/{application_id}", response_model=StandardResponse[dict])
async def get_interview(application_id: int, db: AsyncSession = Depends(get_db), current_user=Depends(require_hr)):
    result = await db.execute(select(Interview).where(Interview.application_id == application_id))
    interview = result.scalar_one_or_none()
    if not interview:
        return StandardResponse.error(message="Interview not found", status_code=404)
    return StandardResponse.ok(data={
        "id": interview.id,
        "scheduled_at": interview.scheduled_at.isoformat() if interview.scheduled_at else None,
        "duration": interview.duration_minutes,
        "location": interview.location,
        "meeting_link": interview.meeting_link,
        "result": interview.result,
    })
