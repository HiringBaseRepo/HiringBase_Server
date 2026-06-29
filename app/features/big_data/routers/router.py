from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database.mongo import get_mongo_db
from app.features.auth.dependencies.auth import require_super_admin
from app.shared.schemas.response import StandardResponse
from app.features.big_data.schemas.schema import (
    BigDataOverview,
    BigDataStats,
    JobListResponse,
    KeywordTrend,
    RefreshResponse
)
from app.features.big_data.services import service

router = APIRouter(prefix="/big-data", tags=["Big Data Market Intelligence"])

@router.get("/overview", response_model=StandardResponse[BigDataOverview])
async def get_overview(
    db: Optional[AsyncIOMotorDatabase] = Depends(get_mongo_db),
    _=Depends(require_super_admin)
):
    result = await service.get_big_data_overview(db)
    return StandardResponse.ok(data=result)

@router.get("/stats", response_model=StandardResponse[BigDataStats])
async def get_stats(
    db: Optional[AsyncIOMotorDatabase] = Depends(get_mongo_db),
    _=Depends(require_super_admin)
):
    result = await service.get_big_data_stats(db)
    return StandardResponse.ok(data=result)

@router.get("/jobs", response_model=StandardResponse[JobListResponse])
async def get_jobs(
    search: Optional[str] = Query(None, description="Search keyword matching title or company"),
    keyword: Optional[str] = Query(None, description="Filter jobs by specific keyword tracked"),
    category: Optional[str] = Query(None, description="Filter jobs by Remotive job category"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("publication_date", description="Field to sort by"),
    sort_dir: str = Query("desc", description="Sort direction (asc/desc)"),
    db: Optional[AsyncIOMotorDatabase] = Depends(get_mongo_db),
    _=Depends(require_super_admin)
):
    result = await service.get_big_data_jobs(
        db, search=search, keyword=keyword, category=category,
        page=page, page_size=page_size, sort_by=sort_by, sort_dir=sort_dir
    )
    return StandardResponse.ok(data=result)

@router.get("/trends", response_model=StandardResponse[List[KeywordTrend]])
async def get_trends(
    days: int = Query(30, ge=7, le=90, description="Number of historical days to fetch trends for"),
    db: Optional[AsyncIOMotorDatabase] = Depends(get_mongo_db),
    _=Depends(require_super_admin)
):
    result = await service.get_big_data_trends(db, days=days)
    return StandardResponse.ok(data=result)

@router.post("/refresh", response_model=StandardResponse[RefreshResponse])
async def trigger_refresh(
    _=Depends(require_super_admin)
):
    result = await service.trigger_scraper_refresh()
    return StandardResponse.ok(data=result)
