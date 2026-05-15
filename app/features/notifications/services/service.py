"""Notification business logic."""
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotificationNotFoundException
from app.core.utils.pagination import PaginationParams
from app.features.audit_logs.models import AuditLog
from app.features.audit_logs.repositories.repository import create_audit_log
from app.features.notifications.models import Notification
from app.features.notifications.repositories.repository import (
    create_notifications_bulk,
    get_notification_by_id,
    get_unread_count,
    list_active_user_ids_by_ids,
    list_internal_recipient_ids,
    list_notifications as list_notifications_query,
    list_unread_notifications,
    mark_all_notifications_read,
    mark_notification_read,
)
from app.features.notifications.schemas.schema import (
    NotificationItem,
    NotificationReadAllResponse,
    NotificationReadResponse,
    NotificationSummaryResponse,
)
from app.features.users.models import User
from app.shared.constants.audit_actions import (
    NOTIFICATION_CREATE,
    NOTIFICATION_MARK_READ,
    NOTIFICATION_MARK_READ_ALL,
)
from app.shared.constants.audit_entities import NOTIFICATION
from app.shared.enums.notification_type import NotificationType
from app.shared.helpers.localization import get_label
from app.shared.schemas.response import PaginatedResponse


NOTIFICATION_MESSAGE_KEYS: dict[NotificationType, tuple[str, str]] = {
    NotificationType.NEW_APPLICATION: (
        "notification.new_application.title",
        "notification.new_application.message",
    ),
    NotificationType.SCREENING_PASSED: (
        "notification.screening_passed.title",
        "notification.screening_passed.message",
    ),
    NotificationType.SCREENING_UNDER_REVIEW: (
        "notification.screening_under_review.title",
        "notification.screening_under_review.message",
    ),
    NotificationType.SCREENING_REJECTED: (
        "notification.screening_rejected.title",
        "notification.screening_rejected.message",
    ),
    NotificationType.DOCUMENT_FAILED: (
        "notification.document_failed.title",
        "notification.document_failed.message",
    ),
    NotificationType.INTERVIEW_SCHEDULED: (
        "notification.interview_scheduled.title",
        "notification.interview_scheduled.message",
    ),
    NotificationType.APPLICATION_OFFERED: (
        "notification.application_offered.title",
        "notification.application_offered.message",
    ),
    NotificationType.APPLICATION_HIRED: (
        "notification.application_hired.title",
        "notification.application_hired.message",
    ),
    NotificationType.APPLICATION_REJECTED: (
        "notification.application_rejected.title",
        "notification.application_rejected.message",
    ),
}


def _resolve_notification_content(notification: Notification) -> tuple[str, str]:
    params = notification.message_params or {}
    return (
        get_label(notification.title, **params),
        get_label(notification.message, **params),
    )


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
            _build_notification_item(item)
            for item in notifications
        ],
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
        total_pages=pages,
        has_next=pagination.page < pages,
        has_prev=pagination.page > 1,
    )


def _build_notification_item(notification: Notification) -> NotificationItem:
    title, message = _resolve_notification_content(notification)
    return NotificationItem(
        id=notification.id,
        type=notification.type,
        title=title,
        message=message,
        is_read=notification.is_read,
        read_at=notification.read_at.isoformat() if notification.read_at else None,
        created_at=notification.created_at.isoformat() if notification.created_at else None,
        entity_type=notification.entity_type,
        entity_id=notification.entity_id,
    )


async def get_summary(db: AsyncSession, *, current_user: User) -> NotificationSummaryResponse:
    unread_count = await get_unread_count(db, user_id=current_user.id)
    return NotificationSummaryResponse(unread_count=unread_count)


async def mark_read(db: AsyncSession, *, current_user: User, notification_id: int) -> NotificationReadResponse:
    from app.core.utils.audit import get_model_snapshot

    notification = await get_notification_by_id(
        db,
        notification_id=notification_id,
        user_id=current_user.id,
    )
    if not notification:
        raise NotificationNotFoundException()
    if notification.is_read:
        return NotificationReadResponse(
            notification_id=notification_id,
            read=True,
            read_at=notification.read_at.isoformat() if notification.read_at else None,
        )

    now = datetime.now(timezone.utc)
    old_values = get_model_snapshot(notification)
    await mark_notification_read(
        db,
        notification_id=notification_id,
        user_id=current_user.id,
        read_at=now,
    )
    await create_audit_log(
        db,
        AuditLog(
            company_id=current_user.company_id,
            user_id=current_user.id,
            action=NOTIFICATION_MARK_READ,
            entity_type=NOTIFICATION,
            entity_id=notification_id,
            old_values=old_values,
            new_values={"is_read": True, "read_at": now.isoformat()},
        ),
    )
    await db.commit()
    return NotificationReadResponse(
        notification_id=notification_id,
        read=True,
        read_at=now.isoformat(),
    )


async def mark_all_read(db: AsyncSession, *, current_user: User) -> NotificationReadAllResponse:
    from app.core.utils.audit import get_model_snapshot

    unread_notifications = await list_unread_notifications(db, user_id=current_user.id)
    now = datetime.now(timezone.utc)
    for notification in unread_notifications:
        await create_audit_log(
            db,
            AuditLog(
                company_id=current_user.company_id,
                user_id=current_user.id,
                action=NOTIFICATION_MARK_READ_ALL,
                entity_type=NOTIFICATION,
                entity_id=notification.id,
                old_values=get_model_snapshot(notification),
                new_values={"is_read": True, "read_at": now.isoformat()},
            ),
        )
    updated_count = await mark_all_notifications_read(
        db,
        user_id=current_user.id,
        read_at=now,
    )
    await db.commit()
    return NotificationReadAllResponse(
        read_all=True,
        updated_count=updated_count,
        read_at=now.isoformat(),
    )


async def create_notification_for_users(
    db: AsyncSession,
    *,
    actor_user_id: int | None,
    company_id: int | None,
    recipient_user_ids: list[int],
    notification_type: NotificationType,
    entity_type: str,
    entity_id: int | None,
    message_params: dict | None = None,
) -> int:
    title_key, message_key = NOTIFICATION_MESSAGE_KEYS[notification_type]
    unique_recipient_ids = sorted(set(recipient_user_ids))
    if not unique_recipient_ids:
        return 0
    notifications = [
        Notification(
            user_id=recipient_user_id,
            type=notification_type,
            title=title_key,
            message=message_key,
            entity_type=entity_type,
            entity_id=entity_id,
            message_params=message_params,
        )
        for recipient_user_id in unique_recipient_ids
    ]
    created_notifications = await create_notifications_bulk(db, notifications)
    for notification in created_notifications:
        await create_audit_log(
            db,
            AuditLog(
                company_id=company_id,
                user_id=actor_user_id,
                action=NOTIFICATION_CREATE,
                entity_type=NOTIFICATION,
                entity_id=notification.id,
                new_values={
                    "recipient_user_id": notification.user_id,
                    "type": notification.type.value,
                    "entity_type": notification.entity_type,
                    "entity_id": notification.entity_id,
                },
            ),
        )
    return len(created_notifications)


async def create_notification_for_internal_audience(
    db: AsyncSession,
    *,
    actor_user_id: int | None,
    company_id: int | None,
    notification_type: NotificationType,
    entity_type: str,
    entity_id: int | None,
    message_params: dict | None = None,
) -> int:
    recipient_ids = await list_internal_recipient_ids(db, company_id=company_id)
    return await create_notification_for_users(
        db,
        actor_user_id=actor_user_id,
        company_id=company_id,
        recipient_user_ids=recipient_ids,
        notification_type=notification_type,
        entity_type=entity_type,
        entity_id=entity_id,
        message_params=message_params,
    )


async def create_notification_for_interviewers(
    db: AsyncSession,
    *,
    actor_user_id: int | None,
    company_id: int | None,
    interviewer_ids: list[int] | None,
    fallback_user_id: int,
    notification_type: NotificationType,
    entity_type: str,
    entity_id: int | None,
    message_params: dict | None = None,
) -> int:
    recipient_ids: list[int] = []
    if interviewer_ids:
        recipient_ids = await list_active_user_ids_by_ids(
            db,
            user_ids=interviewer_ids,
            company_id=company_id,
        )
    if not recipient_ids:
        recipient_ids = [fallback_user_id]
    return await create_notification_for_users(
        db,
        actor_user_id=actor_user_id,
        company_id=company_id,
        recipient_user_ids=recipient_ids,
        notification_type=notification_type,
        entity_type=entity_type,
        entity_id=entity_id,
        message_params=message_params,
    )
