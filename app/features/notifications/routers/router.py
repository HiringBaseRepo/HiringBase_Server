"""Notification API."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.base import get_db
from app.features.auth.dependencies.auth import get_current_user
from app.features.notifications.schemas.schema import NotificationItem, NotificationReadAllResponse, NotificationReadResponse
from app.features.notifications.services.service import (
    list_notifications as list_notifications_service,
    mark_all_read as mark_all_read_service,
    mark_read as mark_read_service,
)
from app.shared.schemas.response import StandardResponse, PaginatedResponse
from app.core.utils.pagination import PaginationParams

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=StandardResponse[PaginatedResponse[NotificationItem]])
async def list_notifications(
    unread_only: bool = False,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await list_notifications_service(
        db,
        current_user=current_user,
        pagination=pagination,
        unread_only=unread_only,
    )
    return StandardResponse.ok(data=result)


@router.post("/{notification_id}/read", response_model=StandardResponse[NotificationReadResponse])
async def mark_read(notification_id: int, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    result = await mark_read_service(db, current_user=current_user, notification_id=notification_id)
    return StandardResponse.ok(data=result)


@router.post("/read-all", response_model=StandardResponse[NotificationReadAllResponse])
async def mark_all_read(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    result = await mark_all_read_service(db, current_user=current_user)
    return StandardResponse.ok(data=result)
