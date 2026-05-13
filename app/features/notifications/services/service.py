"""Notification business logic."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils.pagination import PaginationParams
from app.features.audit_logs.models import AuditLog
from app.features.audit_logs.repositories.repository import create_audit_log
from app.features.notifications.models import Notification
from app.features.users.models import User
from app.features.notifications.repositories.repository import (
    get_notification_by_id,
    list_notifications as list_notifications_query,
    list_unread_notifications,
    mark_all_notifications_read,
    mark_notification_read,
)
from app.features.notifications.schemas.schema import NotificationItem, NotificationReadAllResponse, NotificationReadResponse
from app.shared.schemas.response import PaginatedResponse


async def list_notifications(
    db: AsyncSession,
    *,
    current_user: User,
    pagination: PaginationParams,
    unread_only: bool = False,
) -> PaginatedResponse[NotificationItem]:
    notifications, total = await list_notifications_query(
        db,
        user_id=current_user.id,
        pagination=pagination,
        unread_only=unread_only,
    )
    pages = (total + pagination.per_page - 1) // pagination.per_page
    return PaginatedResponse(
        data=[
            NotificationItem(
                id=item.id,
                type=item.type.value,
                title=item.title,
                message=item.message,
                is_read=item.is_read,
                created_at=item.created_at.isoformat() if item.created_at else None,
            )
            for item in notifications
        ],
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
        total_pages=pages,
        has_next=pagination.page < pages,
        has_prev=pagination.page > 1,
    )


async def mark_read(db: AsyncSession, *, current_user: User, notification_id: int) -> NotificationReadResponse:
    from app.core.utils.audit import get_model_snapshot
    notif = await get_notification_by_id(db, notification_id=notification_id, user_id=current_user.id)
    old_values = get_model_snapshot(notif) if notif else None
    await mark_notification_read(db, notification_id=notification_id, user_id=current_user.id)
    if notif:
        await create_audit_log(
            db,
            AuditLog(
                company_id=current_user.company_id,
                user_id=current_user.id,
                action="NOTIFICATION_MARK_READ",
                entity_type="notification",
                entity_id=notification_id,
                old_values=old_values,
                new_values={"is_read": True},
            ),
        )
    await db.commit()
    return NotificationReadResponse(read=True)


async def mark_all_read(db: AsyncSession, *, current_user: User) -> NotificationReadAllResponse:
    from app.core.utils.audit import get_model_snapshot
    unread_notifications = await list_unread_notifications(db, user_id=current_user.id)
    for notif in unread_notifications:
        await create_audit_log(
            db,
            AuditLog(
                company_id=current_user.company_id,
                user_id=current_user.id,
                action="NOTIFICATION_MARK_READ_ALL",
                entity_type="notification",
                entity_id=notif.id,
                old_values=get_model_snapshot(notif),
                new_values={"is_read": True},
            ),
        )
    await mark_all_notifications_read(db, user_id=current_user.id)
    await db.commit()
    return NotificationReadAllResponse(read_all=True)
