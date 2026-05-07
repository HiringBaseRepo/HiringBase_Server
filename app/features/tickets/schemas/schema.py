"""Ticket schemas."""
from pydantic import BaseModel


class TicketTrackResponse(BaseModel):
    ticket_code: str
    status: str
    status_label: str | None = None
    subject: str | None
    application_status: str | None
    application_status_label: str | None = None
    job_title: str | None
    applicant_name: str | None
    notes: str | None
    created_at: str | None
    resolved_at: str | None
