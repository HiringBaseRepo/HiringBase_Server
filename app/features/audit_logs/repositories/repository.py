"""Audit log data access helpers."""
from datetime import datetime, time
from sqlalchemy import func, select, or_
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
    
    # 1. Base query for data
    stmt = select(AuditLog).join(AuditLog.user, isouter=True)
    count_stmt = select(func.count(AuditLog.id)).join(AuditLog.user, isouter=True)
    
    # 2. Prepare Filters
    filters = []
    
    if current_user_role == UserRole.HR:
        filters.append(AuditLog.company_id == current_user_company_id)
    
    if entity_type is not None and entity_type.strip() != "":
        filters.append(AuditLog.entity_type == entity_type)
    
    if entity_id:
        filters.append(AuditLog.entity_id == entity_id)

    if search and search.strip():
        search_filter = f"%{search}%"
        filters.append(
            or_(
                AuditLog.action.ilike(search_filter),
                AuditLog.entity_type.ilike(search_filter),
                AuditLog.ip_address.ilike(search_filter),
                func.coalesce(User.full_name, "").ilike(search_filter)
            )
        )

    # Date Filtering - Fix for ProgrammingError (timestamp vs varchar)
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date)
            filters.append(AuditLog.created_at >= start_dt)
        except ValueError:
            pass
            
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date)
            # If it's just a date (00:00:00), make it end of day for inclusive search
            if end_dt.time() == time(0, 0, 0):
                end_dt = end_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
            filters.append(AuditLog.created_at <= end_dt)
        except ValueError:
            pass

    # 3. Apply filters to both statements
    if filters:
        stmt = stmt.where(*filters)
        count_stmt = count_stmt.where(*filters)

    # 4. Get total count
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # 5. Get paginated data with options
    data_stmt = stmt.options(selectinload(AuditLog.user)).order_by(AuditLog.created_at.desc())
    data_stmt = data_stmt.offset(pagination.offset).limit(pagination.limit)
    
    result = await db.execute(data_stmt)
    logs_data = result.scalars().all()
    
    return list(logs_data), total


async def create_audit_log(db: AsyncSession, audit: AuditLog) -> None:
    """Save an audit log entry with automatic context injection."""
    from app.core.context.audit import get_client_ip, get_user_agent
    
    if not audit.ip_address:
        audit.ip_address = get_client_ip()
    if not audit.user_agent:
        audit.user_agent = get_user_agent()
        
    db.add(audit)
