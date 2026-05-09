"""Audit log data access helpers."""
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
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
    search: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> tuple[list[AuditLog], int]:
    from app.features.users.models import User
    
    stmt = select(AuditLog).options(selectinload(AuditLog.user)).join(AuditLog.user, isouter=True)
    
    if current_user_role == UserRole.HR:
        stmt = stmt.where(AuditLog.company_id == current_user_company_id)
    
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    
    if entity_id:
        stmt = stmt.where(AuditLog.entity_id == entity_id)

    if search:
        search_filter = f"%{search}%"
        stmt = stmt.where(
            (AuditLog.action.ilike(search_filter)) | 
            (User.full_name.ilike(search_filter)) |
            (AuditLog.entity_type.ilike(search_filter))
        )

    if start_date:
        stmt = stmt.where(AuditLog.created_at >= start_date)
    if end_date:
        stmt = stmt.where(AuditLog.created_at <= end_date)

    total_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_result.scalar_one()
    result = await db.execute(
        stmt.order_by(AuditLog.created_at.desc()).offset(pagination.offset).limit(pagination.limit)
    )
    logs_data = result.scalars().all()
    return list(logs_data), total


async def create_audit_log(db: AsyncSession, audit: AuditLog) -> None:
    """Save an audit log entry."""
    db.add(audit)
