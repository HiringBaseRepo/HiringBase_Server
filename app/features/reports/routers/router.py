from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database.base import get_db
from app.features.auth.dependencies.auth import require_super_admin
from app.features.reports.schemas.schema import ReportStats
from app.features.reports.services.service import get_report_stats
from app.shared.schemas.response import StandardResponse

router = APIRouter(prefix="/reports", tags=["Reports"])

@router.get("/stats", response_model=StandardResponse[ReportStats])
async def stats(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: AsyncSession = Depends(get_db), 
    _=Depends(require_super_admin)
):
    result = await get_report_stats(db, start_date, end_date)
    return StandardResponse.ok(data=result)
