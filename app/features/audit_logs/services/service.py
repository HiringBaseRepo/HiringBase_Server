"""Audit log business logic."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils.pagination import PaginationParams
from app.features.audit_logs.repositories.repository import list_audit_logs as list_audit_logs_query
from app.features.audit_logs.schemas.schema import AuditLogItem
from app.features.users.models import User
from app.shared.schemas.response import PaginatedResponse


from app.shared.helpers.localization import get_label


def _build_initials(full_name: str | None, fallback: str) -> str:
    if not full_name:
        return fallback

    parts = [part[0] for part in full_name.split() if part]
    if not parts:
        return fallback
    return "".join(parts[:2]).upper()


async def list_audit_logs(
    db: AsyncSession,
    *,
    current_user: User,
    pagination: PaginationParams,
    entity_type: str | None = None,
    entity_id: int | None = None,
    search: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> PaginatedResponse[AuditLogItem]:
    logs, total = await list_audit_logs_query(
        db,
        pagination=pagination,
        current_user_role=current_user.role,
        current_user_company_id=current_user.company_id,
        entity_type=entity_type,
        entity_id=entity_id,
        search=search,
        start_date=start_date,
        end_date=end_date,
    )
    pages = (total + pagination.per_page - 1) // pagination.per_page
    return PaginatedResponse(
        data=[
            AuditLogItem(
                id=log.id,
                action=log.action,
                action_label=get_label(log.action),
                entity_type=log.entity_type,
                entity_id=log.entity_id,
                user_name=log.user.full_name if log.user else "System Administrator",
                user_initials=_build_initials(
                    log.user.full_name if log.user else None,
                    "SA",
                ),
                actor_type="user" if log.user else "system",
                actor_role_label=(
                    get_label(log.user.role) if log.user else "Automated Process"
                ),
                ip_address=log.ip_address,
                ip_address_display=log.ip_address or (
                    "System Event" if not log.user else None
                ),
                user_agent=log.user_agent,
                user_agent_display=log.user_agent or (
                    "Background Worker" if not log.user else None
                ),
                old_values=log.old_values,
                new_values=log.new_values,
                created_at=log.created_at.isoformat() if log.created_at else None,
            )
            for log in logs
        ],
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
        total_pages=pages,
        has_next=pagination.page < pages,
        has_prev=pagination.page > 1,
    )
