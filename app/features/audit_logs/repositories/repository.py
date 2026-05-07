"""Audit log data access helpers."""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils.pagination import PaginationParams
from app.features.audit_logs.models import AuditLog
from app.shared.enums.user_roles import UserRole


async def list_audit_logs(
    db: AsyncSession,
    *,
    pagination: PaginationParams,
    current_user_role: UserRole,
    current_user_company_id: int | None,
    entity_type: str | None = None,
    entity_id: int | None = None,
) -> tuple[list[AuditLog], int]:
    stmt = select(AuditLog)
    if current_user_role == UserRole.HR:
        stmt = stmt.where(AuditLog.company_id == current_user_company_id)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(AuditLog.entity_id == entity_id)

    total_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_result.scalar_one()
    result = await db.execute(
        stmt.order_by(AuditLog.created_at.desc()).offset(pagination.offset).limit(pagination.limit)
    )
    return list(result.scalars().all()), total


async def create_audit_log(db: AsyncSession, audit: AuditLog) -> None:
    """Save an audit log entry."""
    db.add(audit)
