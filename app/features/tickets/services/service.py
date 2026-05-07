"""Ticket tracking business logic."""
from app.core.exceptions import TicketNotFoundException
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.tickets.repositories.repository import (
    get_application_by_id,
    get_job_by_id,
    get_ticket_by_code,
    get_user_by_id,
)
from app.features.tickets.schemas.schema import TicketTrackResponse


from app.shared.helpers.localization import get_label


async def track_ticket(db: AsyncSession, ticket_code: str) -> TicketTrackResponse:
    ticket = await get_ticket_by_code(db, ticket_code)
    if not ticket:
        raise TicketNotFoundException()

    application = await get_application_by_id(db, ticket.application_id)
    job = await get_job_by_id(db, application.job_id) if application else None
    applicant = await get_user_by_id(db, application.applicant_id) if application else None
    return TicketTrackResponse(
        ticket_code=ticket.code,
        status=ticket.status.value,
        status_label=get_label(ticket.status),
        subject=ticket.subject,
        application_status=application.status.value if application else None,
        application_status_label=get_label(application.status) if application else None,
        job_title=job.title if job else None,
        applicant_name=applicant.full_name if applicant else None,
        notes=ticket.notes,
        created_at=ticket.created_at.isoformat() if ticket.created_at else None,
        resolved_at=ticket.resolved_at.isoformat() if ticket.resolved_at else None,
    )
