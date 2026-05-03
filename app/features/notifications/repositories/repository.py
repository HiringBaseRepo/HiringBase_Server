"""Notification data access helpers."""
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils.pagination import PaginationParams
from app.features.models import Notification


async def list_notifications(
    db: AsyncSession,
    *,
    user_id: int,
    pagination: PaginationParams,
    unread_only: bool = False,
) -> tuple[list[Notification], int]:
    stmt = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        stmt = stmt.where(Notification.is_read == False)

    total_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_result.scalar_one()
    result = await db.execute(
        stmt.order_by(Notification.created_at.desc()).offset(pagination.offset).limit(pagination.limit)
    )
    return list(result.scalars().all()), total


async def mark_notification_read(db: AsyncSession, *, notification_id: int, user_id: int) -> None:
    await db.execute(
        update(Notification)
        .where(Notification.id == notification_id, Notification.user_id == user_id)
        .values(is_read=True)
    )


async def mark_all_notifications_read(db: AsyncSession, *, user_id: int) -> None:
    await db.execute(
        update(Notification)
        .where(Notification.user_id == user_id, Notification.is_read == False)
        .values(is_read=True)
    )
