"""Notification API."""
from fastapi import APIRouter, Depends

from app.features.auth.dependencies.auth import CurrentUserDep, DbDep
from app.features.notifications.schemas.schema import (
    NotificationItem,
    NotificationReadAllResponse,
    NotificationReadResponse,
    NotificationSummaryResponse,
)
from app.features.notifications.services.service import (
    get_summary as get_summary_service,
    list_notifications as list_notifications_service,
    mark_all_read as mark_all_read_service,
    mark_read as mark_read_service,
)
from app.core.utils.pagination import PaginationParams
from app.shared.schemas.response import PaginatedResponse, StandardResponse

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=StandardResponse[PaginatedResponse[NotificationItem]])
async def list_notifications(
    db: DbDep,
    current_user: CurrentUserDep,
    unread_only: bool = False,
    pagination: PaginationParams = Depends(),
):
    result = await list_notifications_service(
        db,
        current_user=current_user,
        pagination=pagination,
        unread_only=unread_only,
    )
    return StandardResponse.ok(data=result)


@router.get("/summary", response_model=StandardResponse[NotificationSummaryResponse])
async def summary(db: DbDep, current_user: CurrentUserDep):
    result = await get_summary_service(db, current_user=current_user)
    return StandardResponse.ok(data=result)


@router.post("/{notification_id}/read", response_model=StandardResponse[NotificationReadResponse])
async def mark_read(notification_id: int, db: DbDep, current_user: CurrentUserDep):
    result = await mark_read_service(db, current_user=current_user, notification_id=notification_id)
    return StandardResponse.ok(data=result)


@router.post("/read-all", response_model=StandardResponse[NotificationReadAllResponse])
async def mark_all_read(db: DbDep, current_user: CurrentUserDep):
    result = await mark_all_read_service(db, current_user=current_user)
    return StandardResponse.ok(data=result)
