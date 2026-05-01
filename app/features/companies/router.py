"""Super Admin Company Management API."""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database.base import get_db
from app.features.auth.dependencies import require_super_admin, get_current_user
from app.features.models import Company, User
from app.shared.schemas.response import StandardResponse, PaginatedResponse
from app.core.utils.pagination import PaginationParams

router = APIRouter(prefix="/companies", tags=["Companies — Super Admin"])


@router.post("", response_model=StandardResponse[dict])
async def create_company(
    name: str,
    slug: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_super_admin),
):
    company = Company(name=name, slug=slug)
    db.add(company)
    await db.commit()
    await db.refresh(company)
    return StandardResponse.ok(data={
        "id": company.id,
        "name": company.name,
        "slug": company.slug,
        "is_active": company.is_active,
    })


@router.get("", response_model=StandardResponse[PaginatedResponse[dict]])
async def list_companies(
    q: Optional[str] = None,
    is_active: Optional[bool] = None,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_super_admin),
):
    stmt = select(Company).where(Company.deleted_at.is_(None))
    if q:
        stmt = stmt.where(Company.name.ilike(f"%{q}%"))
    if is_active is not None:
        stmt = stmt.where(Company.is_active == is_active)

    total_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_result.scalar_one()

    stmt = stmt.offset(pagination.offset).limit(pagination.limit)
    result = await db.execute(stmt)
    items = []
    for c in result.scalars().all():
        items.append({
            "id": c.id, "name": c.name, "slug": c.slug,
            "is_active": c.is_active, "is_suspended": c.is_suspended,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })

    pages = (total + pagination.per_page - 1) // pagination.per_page
    return StandardResponse.ok(data=PaginatedResponse(
        data=items, total=total, page=pagination.page,
        per_page=pagination.per_page, total_pages=pages,
        has_next=pagination.page < pages, has_prev=pagination.page > 1,
    ))


@router.patch("/{company_id}/suspend", response_model=StandardResponse[dict])
async def suspend_company(company_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_super_admin)):
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        return StandardResponse.error(message="Company not found", status_code=404)
    company.is_suspended = True
    await db.commit()
    return StandardResponse.ok(data={"id": company.id, "is_suspended": True})


@router.patch("/{company_id}/activate", response_model=StandardResponse[dict])
async def activate_company(company_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_super_admin)):
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        return StandardResponse.error(message="Company not found", status_code=404)
    company.is_suspended = False
    company.is_active = True
    await db.commit()
    return StandardResponse.ok(data={"id": company.id, "is_active": True, "is_suspended": False})


@router.get("/{company_id}/statistics", response_model=StandardResponse[dict])
async def company_statistics(company_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_super_admin)):
    from app.features.models import Job, Application
    job_count = await db.execute(select(func.count()).where(Job.company_id == company_id, Job.deleted_at.is_(None)))
    app_count = await db.execute(select(func.count()).where(
        Application.job_id.in_(select(Job.id).where(Job.company_id == company_id)),
        Application.deleted_at.is_(None)
    ))
    return StandardResponse.ok(data={
        "company_id": company_id,
        "total_jobs": job_count.scalar_one(),
        "total_applications": app_count.scalar_one(),
    })
