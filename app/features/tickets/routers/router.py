"""Ticket Tracking API."""
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database.base import get_db
from app.features.auth.dependencies import get_current_user
from app.features.models import Ticket, Application, Job, User
from app.shared.schemas.response import StandardResponse

router = APIRouter(prefix="/tickets", tags=["Tickets"])


@router.get("/track/{ticket_code}", response_model=StandardResponse[dict])
async def track_ticket(ticket_code: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Ticket).where(Ticket.code == ticket_code))
    ticket = result.scalar_one_or_none()
    if not ticket:
        return StandardResponse.error(message="Ticket not found", status_code=404)

    app_result = await db.execute(select(Application).where(Application.id == ticket.application_id))
    application = app_result.scalar_one_or_none()

    job_result = await db.execute(select(Job).where(Job.id == application.job_id)) if application else None
    job = job_result.scalar_one_or_none() if job_result else None

    applicant_result = await db.execute(select(User).where(User.id == application.applicant_id)) if application else None
    applicant = applicant_result.scalar_one_or_none() if applicant_result else None

    return StandardResponse.ok(data={
        "ticket_code": ticket.code,
        "status": ticket.status.value,
        "subject": ticket.subject,
        "application_status": application.status.value if application else None,
        "job_title": job.title if job else None,
        "applicant_name": applicant.full_name if applicant else None,
        "notes": ticket.notes,
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        "resolved_at": ticket.resolved_at.isoformat() if ticket.resolved_at else None,
    })
