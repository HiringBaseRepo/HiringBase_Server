from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database.base import get_db
from app.features.auth.dependencies.auth import require_super_admin
from app.features.dashboard.schemas.schema import DashboardOverview, RecentCampaign
from app.features.dashboard.services.service import get_dashboard_overview, get_recent_campaigns
from app.shared.schemas.response import StandardResponse
from typing import List

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/overview", response_model=StandardResponse[DashboardOverview])
async def overview(db: AsyncSession = Depends(get_db), _=Depends(require_super_admin)):
    result = await get_dashboard_overview(db)
    return StandardResponse.ok(data=result)

@router.get("/campaigns", response_model=StandardResponse[List[RecentCampaign]])
async def campaigns(db: AsyncSession = Depends(get_db), _=Depends(require_super_admin)):
    result = await get_recent_campaigns(db)
    return StandardResponse.ok(data=result)
