"""Notification API."""
from typing import Optional, List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func

from app.core.database.base import get_db
from app.features.auth.dependencies import get_current_user
from app.features.models import Notification
from app.shared.schemas.response import StandardResponse, PaginatedResponse
from app.core.utils.pagination import PaginationParams

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=StandardResponse[PaginatedResponse[dict]])
async def list_notifications(
    unread_only: bool = False,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    stmt = select(Notification).where(Notification.user_id == current_user.id)
    if unread_only:
        stmt = stmt.where(Notification.is_read == False)

    total_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_result.scalar_one()

    stmt = stmt.order_by(Notification.created_at.desc()).offset(pagination.offset).limit(pagination.limit)
    result = await db.execute(stmt)
    items = []
    for n in result.scalars().all():
        items.append({
            "id": n.id, "type": n.type.value, "title": n.title,
            "message": n.message, "is_read": n.is_read,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        })

    pages = (total + pagination.per_page - 1) // pagination.per_page
    return StandardResponse.ok(data=PaginatedResponse(
        data=items, total=total, page=pagination.page,
        per_page=pagination.per_page, total_pages=pages,
        has_next=pagination.page < pages, has_prev=pagination.page > 1,
    ))


@router.post("/{notification_id}/read", response_model=StandardResponse[dict])
async def mark_read(notification_id: int, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    await db.execute(
        update(Notification).where(Notification.id == notification_id, Notification.user_id == current_user.id)
        .values(is_read=True)
    )
    await db.commit()
    return StandardResponse.ok(data={"read": True})


@router.post("/read-all", response_model=StandardResponse[dict])
async def mark_all_read(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    await db.execute(
        update(Notification).where(Notification.user_id == current_user.id, Notification.is_read == False)
        .values(is_read=True)
    )
    await db.commit()
    return StandardResponse.ok(data={"read_all": True})
