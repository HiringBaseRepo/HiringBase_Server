"""Notification data access helpers."""
from datetime import datetime
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils.pagination import PaginationParams
from app.features.notifications.models import Notification
from app.features.users.models import User
from app.shared.enums.user_roles import UserRole


async def list_notifications(
    db: AsyncSession,
    *,
    user_id: int,
    pagination: PaginationParams,
    unread_only: bool = False,
) -> tuple[list[Notification], int]:
    stmt = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        stmt = stmt.where(~Notification.is_read)

    total_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_result.scalar_one()
    result = await db.execute(
        stmt.order_by(Notification.created_at.desc()).offset(pagination.offset).limit(pagination.limit)
    )
    return list(result.scalars().all()), total


async def create_notification(db: AsyncSession, notification: Notification) -> Notification:
    db.add(notification)
    await db.flush()
    await db.refresh(notification)
    return notification


async def create_notifications_bulk(db: AsyncSession, notifications: list[Notification]) -> list[Notification]:
    if not notifications:
        return []
    db.add_all(notifications)
    await db.flush()
    for notification in notifications:
        await db.refresh(notification)
    return notifications


async def mark_notification_read(
    db: AsyncSession,
    *,
    notification_id: int,
    user_id: int,
    read_at: datetime,
) -> None:
    await db.execute(
        update(Notification)
        .where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
            ~Notification.is_read,
        )
        .values(is_read=True, read_at=read_at)
    )


async def mark_all_notifications_read(
    db: AsyncSession,
    *,
    user_id: int,
    read_at: datetime,
) -> int:
    result = await db.execute(
        update(Notification)
        .where(Notification.user_id == user_id, ~Notification.is_read)
        .values(is_read=True, read_at=read_at)
    )
    return result.rowcount or 0


async def get_notification_by_id(
    db: AsyncSession, *, notification_id: int, user_id: int
) -> Notification | None:
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def list_unread_notifications(db: AsyncSession, *, user_id: int) -> list[Notification]:
    result = await db.execute(
        select(Notification).where(
            Notification.user_id == user_id,
            ~Notification.is_read,
        )
    )
    return list(result.scalars().all())


async def get_unread_count(db: AsyncSession, *, user_id: int) -> int:
    result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == user_id,
            ~Notification.is_read,
        )
    )
    return result.scalar_one()


async def list_internal_recipient_ids(db: AsyncSession, *, company_id: int | None) -> list[int]:
    result = await db.execute(
        select(User.id).where(
            User.is_active.is_(True),
            User.deleted_at.is_(None),
            (
                ((User.role == UserRole.HR) & (User.company_id == company_id))
                | (User.role == UserRole.SUPER_ADMIN)
            ),
        )
    )
    return [user_id for user_id in result.scalars().all()]


async def list_active_user_ids_by_ids(
    db: AsyncSession,
    *,
    user_ids: list[int],
    company_id: int | None = None,
) -> list[int]:
    if not user_ids:
        return []
    stmt = select(User.id).where(
        User.id.in_(user_ids),
        User.is_active.is_(True),
        User.deleted_at.is_(None),
    )
    if company_id is not None:
        stmt = stmt.where(User.company_id == company_id)
    result = await db.execute(stmt)
    return [user_id for user_id in result.scalars().all()]
