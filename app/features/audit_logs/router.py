"""Audit Logs API."""
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database.base import get_db
from app.features.auth.dependencies import require_super_admin, require_hr, get_current_user
from app.features.models import AuditLog
from app.shared.schemas.response import StandardResponse, PaginatedResponse
from app.core.utils.pagination import PaginationParams
from app.shared.enums.user_roles import UserRole

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get("", response_model=StandardResponse[PaginatedResponse[dict]])
async def list_audit_logs(
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    stmt = select(AuditLog)
    if current_user.role == UserRole.HR:
        stmt = stmt.where(AuditLog.company_id == current_user.company_id)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(AuditLog.entity_id == entity_id)

    total_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_result.scalar_one()

    stmt = stmt.order_by(AuditLog.created_at.desc()).offset(pagination.offset).limit(pagination.limit)
    result = await db.execute(stmt)
    items = []
    for log in result.scalars().all():
        items.append({
            "id": log.id, "action": log.action, "entity_type": log.entity_type,
            "entity_id": log.entity_id, "old_values": log.old_values,
            "new_values": log.new_values, "created_at": log.created_at.isoformat() if log.created_at else None,
        })

    pages = (total + pagination.per_page - 1) // pagination.per_page
    return StandardResponse.ok(data=PaginatedResponse(
        data=items, total=total, page=pagination.page,
        per_page=pagination.per_page, total_pages=pages,
        has_next=pagination.page < pages, has_prev=pagination.page > 1,
    ))
