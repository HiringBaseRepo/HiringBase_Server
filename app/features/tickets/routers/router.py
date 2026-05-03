"""Ticket Tracking API."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.base import get_db
from app.features.tickets.schemas.schema import TicketTrackResponse
from app.features.tickets.services.service import track_ticket as track_ticket_service
from app.shared.schemas.response import StandardResponse

router = APIRouter(prefix="/tickets", tags=["Tickets"])


@router.get("/track/{ticket_code}", response_model=StandardResponse[TicketTrackResponse])
async def track_ticket(ticket_code: str, db: AsyncSession = Depends(get_db)):
    result = await track_ticket_service(db, ticket_code)
    return StandardResponse.ok(data=result)
