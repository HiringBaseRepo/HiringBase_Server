"""Super Admin Company Management API."""
from typing import Optional
from fastapi import APIRouter, Depends, File, UploadFile, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.base import get_db
from app.features.auth.dependencies.auth import require_super_admin
from app.features.users.models import User
from app.features.companies.schemas.schema import (
    CompanyActivateResponse,
    CompanyCreatedResponse,
    CompanyDetailResponse,
    CompanyListItem,
    CompanyOverviewResponse,
    CompanyStatisticsResponse,
    CompanySuspendResponse,
    CreateCompanyRequest,
)
from app.features.companies.services.service import (
    activate_company as activate_company_service,
    create_company as create_company_service,
    get_company_by_id as get_company_service,
    get_company_statistics,
    get_multi_company_overview,
    list_companies as list_companies_service,
    suspend_company as suspend_company_service,
    update_company as update_company_service,
    upload_logo as upload_logo_service,
)
from app.shared.schemas.response import StandardResponse, PaginatedResponse
from app.core.utils.pagination import PaginationParams

router = APIRouter(prefix="/companies", tags=["Companies — Super Admin"])


@router.post("", response_model=StandardResponse[CompanyCreatedResponse])
async def create_company(
    data: CreateCompanyRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    result = await create_company_service(
        db, data, current_user=current_user, ip_address=request.client.host
    )
    return StandardResponse.ok(data=result)


@router.get("", response_model=StandardResponse[PaginatedResponse[CompanyListItem]])
async def list_companies(
    q: Optional[str] = None,
    industry: Optional[str] = None,
    is_active: Optional[bool] = None,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_super_admin),
):
    result = await list_companies_service(db, pagination=pagination, q=q, industry=industry, is_active=is_active)
    return StandardResponse.ok(data=result)


@router.patch("/{company_id}/suspend", response_model=StandardResponse[CompanySuspendResponse])
async def suspend_company(
    company_id: int, 
    request: Request,
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(require_super_admin)
):
    result = await suspend_company_service(
        db, company_id, current_user=current_user, ip_address=request.client.host
    )
    return StandardResponse.ok(data=result)


@router.patch("/{company_id}/activate", response_model=StandardResponse[CompanyActivateResponse])
async def activate_company(
    company_id: int, 
    request: Request,
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(require_super_admin)
):
    result = await activate_company_service(
        db, company_id, current_user=current_user, ip_address=request.client.host
    )
    return StandardResponse.ok(data=result)


@router.get("/{company_id}", response_model=StandardResponse[CompanyDetailResponse])
async def get_company(company_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_super_admin)):
    result = await get_company_service(db, company_id)
    return StandardResponse.ok(data=result)


@router.patch("/{company_id}", response_model=StandardResponse[CompanyDetailResponse])
async def update_company(
    company_id: int,
    data: CreateCompanyRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    result = await update_company_service(
        db, company_id, data, current_user=current_user, ip_address=request.client.host
    )
    return StandardResponse.ok(data=result)


@router.get("/{company_id}/statistics", response_model=StandardResponse[CompanyStatisticsResponse])
async def company_statistics(company_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_super_admin)):
    """Statistik lengkap satu perusahaan untuk Super Admin."""
    result = await get_company_statistics(db, company_id)
    return StandardResponse.ok(data=result)


@router.get("/overview", response_model=StandardResponse[CompanyOverviewResponse])
async def multi_company_overview(db: AsyncSession = Depends(get_db), _=Depends(require_super_admin)):
    """Overview semua perusahaan untuk Super Admin dashboard."""
    result = await get_multi_company_overview(db)
    return StandardResponse.ok(data=result)


@router.post("/upload-logo", response_model=StandardResponse[dict])
async def upload_company_logo(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_super_admin),
):
    """Upload logo perusahaan ke Cloudflare R2."""
    url = await upload_logo_service(db, file)
    return StandardResponse.ok(data={"logo_url": url})
