"""Interview business logic."""
from app.core.exceptions import ApplicationNotFoundException, InterviewNotFoundException
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.audit_logs.models import AuditLog
from app.features.audit_logs.repositories.repository import create_audit_log
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
from app.features.interviews.models import Interview
from app.features.users.models import User
from app.shared.constants.audit_actions import INTERVIEW_SCHEDULE
from app.shared.tasks.mail_tasks import send_interview_invite



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
        raise ApplicationNotFoundException()

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
    await create_audit_log(
        db,
        AuditLog(
            company_id=current_user.company_id,
            user_id=current_user.id,
            action=INTERVIEW_SCHEDULE,
            entity_type="interview",
            entity_id=interview.id,
            new_values={
                "application_id": data.application_id,
                "scheduled_at": data.scheduled_at.isoformat(),
                "duration_minutes": data.duration_minutes,
                "interview_type": data.interview_type,
                "location_or_meeting_link": data.meeting_link or data.location,
            },
        ),
    )
    await db.commit()

    # Trigger Background Task: Send Interview Invite to Applicant
    if application.applicant:
        await send_interview_invite.kiq(
            email=application.applicant.email,
            name=application.applicant.full_name,
            job_title=application.job.title if application.job else "Posisi",
            time=data.scheduled_at.strftime("%d %B %Y, %H:%M"),
            location=data.meeting_link or data.location or "Online"
        )
    
    # Trigger Background Task: Send Interview Invite to HR (Interviewer)
    await send_interview_invite.kiq(
        email=current_user.email,
        name=current_user.full_name,
        job_title=application.job.title if application.job else "Posisi",
        time=data.scheduled_at.strftime("%d %B %Y, %H:%M"),
        location=data.meeting_link or data.location or "Online"
    )

    return InterviewScheduledResponse(
        interview_id=interview.id,
        scheduled_at=data.scheduled_at.isoformat(),
    )


async def get_interview(db: AsyncSession, application_id: int) -> InterviewDetailResponse:
    interview = await get_interview_by_application_id(db, application_id)
    if not interview:
        raise InterviewNotFoundException()
    return InterviewDetailResponse(
        id=interview.id,
        scheduled_at=interview.scheduled_at.isoformat() if interview.scheduled_at else None,
        duration=interview.duration_minutes,
        location=interview.location,
        meeting_link=interview.meeting_link,
        result=interview.result,
    )
