"""Super Admin Company Management API."""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database.base import get_db
from app.features.auth.dependencies.auth import require_super_admin, get_current_user
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
    """Statistik lengkap satu perusahaan untuk Super Admin."""
    from app.features.models import Job, Application, User as UserModel
    from app.shared.enums.application_status import ApplicationStatus
    from app.shared.enums.job_status import JobStatus
    from app.shared.enums.user_roles import UserRole

    # Cek company exists
    comp_result = await db.execute(select(Company).where(Company.id == company_id))
    company = comp_result.scalar_one_or_none()
    if not company:
        return StandardResponse.error(message="Company not found", status_code=404)

    # Total jobs per status
    job_count = await db.execute(
        select(func.count()).where(Job.company_id == company_id, Job.deleted_at.is_(None))
    )
    published_jobs = await db.execute(
        select(func.count()).where(
            Job.company_id == company_id,
            Job.status == JobStatus.PUBLISHED,
            Job.deleted_at.is_(None),
        )
    )

    # Total applications
    app_count = await db.execute(
        select(func.count()).where(
            Application.job_id.in_(select(Job.id).where(Job.company_id == company_id)),
            Application.deleted_at.is_(None),
        )
    )

    # Hired count
    hired_count = await db.execute(
        select(func.count()).where(
            Application.job_id.in_(select(Job.id).where(Job.company_id == company_id)),
            Application.status == ApplicationStatus.HIRED,
            Application.deleted_at.is_(None),
        )
    )

    # Rejected count
    rejected_count = await db.execute(
        select(func.count()).where(
            Application.job_id.in_(select(Job.id).where(Job.company_id == company_id)),
            Application.status == ApplicationStatus.REJECTED,
            Application.deleted_at.is_(None),
        )
    )

    # HR users count
    hr_count = await db.execute(
        select(func.count()).where(
            UserModel.company_id == company_id,
            UserModel.role == UserRole.HR,
            UserModel.deleted_at.is_(None),
        )
    )

    return StandardResponse.ok(data={
        "company_id": company_id,
        "company_name": company.name,
        "is_active": company.is_active,
        "is_suspended": company.is_suspended,
        "stats": {
            "total_jobs": job_count.scalar_one(),
            "published_jobs": published_jobs.scalar_one(),
            "total_applications": app_count.scalar_one(),
            "total_hired": hired_count.scalar_one(),
            "total_rejected": rejected_count.scalar_one(),
            "hr_users": hr_count.scalar_one(),
        },
    })


@router.get("/overview", response_model=StandardResponse[dict])
async def multi_company_overview(db: AsyncSession = Depends(get_db), _=Depends(require_super_admin)):
    """Overview semua perusahaan untuk Super Admin dashboard."""
    from app.features.models import Job, Application

    result = await db.execute(select(Company).where(Company.deleted_at.is_(None)).order_by(Company.created_at.desc()))
    companies = result.scalars().all()

    total_companies = len(companies)
    active_companies = sum(1 for c in companies if c.is_active and not c.is_suspended)
    suspended_companies = sum(1 for c in companies if c.is_suspended)

    # Aggregate stats
    total_jobs_all = await db.execute(select(func.count(Job.id)).where(Job.deleted_at.is_(None)))
    total_apps_all = await db.execute(select(func.count(Application.id)).where(Application.deleted_at.is_(None)))

    companies_summary = []
    for c in companies:
        job_ct = await db.execute(
            select(func.count()).where(Job.company_id == c.id, Job.deleted_at.is_(None))
        )
        app_ct = await db.execute(
            select(func.count()).where(
                Application.job_id.in_(select(Job.id).where(Job.company_id == c.id)),
                Application.deleted_at.is_(None),
            )
        )
        companies_summary.append({
            "id": c.id,
            "name": c.name,
            "slug": c.slug,
            "is_active": c.is_active,
            "is_suspended": c.is_suspended,
            "total_jobs": job_ct.scalar_one(),
            "total_applications": app_ct.scalar_one(),
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })

    return StandardResponse.ok(data={
        "summary": {
            "total_companies": total_companies,
            "active_companies": active_companies,
            "suspended_companies": suspended_companies,
            "total_jobs_platform": total_jobs_all.scalar_one(),
            "total_applications_platform": total_apps_all.scalar_one(),
        },
        "companies": companies_summary,
    })
