"""Interview schemas."""
from datetime import datetime
from pydantic import BaseModel
from app.shared.enums.interview import InterviewResult, InterviewType


class ScheduleInterviewRequest(BaseModel):
    application_id: int
    scheduled_at: datetime
    duration_minutes: int = 60
    location: str | None = None
    meeting_link: str | None = None
    interview_type: InterviewType = InterviewType.IN_PERSON
    interviewer_ids: list | None = None


class InterviewScheduledResponse(BaseModel):
    interview_id: int
    scheduled_at: str


class InterviewDetailResponse(BaseModel):
    id: int
    scheduled_at: str | None
    duration: int
    location: str | None
    meeting_link: str | None
    result: InterviewResult | None
