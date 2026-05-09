"""Audit Logs API."""
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.base import get_db
from app.features.auth.dependencies.auth import get_current_user
from app.features.audit_logs.schemas.schema import AuditLogItem
from app.features.audit_logs.services.service import list_audit_logs as list_audit_logs_service
from app.shared.schemas.response import StandardResponse, PaginatedResponse
from app.core.utils.pagination import PaginationParams

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get("", response_model=StandardResponse[PaginatedResponse[AuditLogItem]])
async def list_audit_logs(
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    search: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await list_audit_logs_service(
        db,
        current_user=current_user,
        pagination=pagination,
        entity_type=entity_type,
        entity_id=entity_id,
        search=search,
        start_date=start_date,
        end_date=end_date,
    )
    return StandardResponse.ok(data=result)
