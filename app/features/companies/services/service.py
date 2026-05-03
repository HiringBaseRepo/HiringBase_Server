"""Company management business logic."""
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils.pagination import PaginationParams
from app.features.companies.repositories.repository import (
    count_applications,
    count_hr_users,
    count_jobs,
    get_company_by_id,
    list_all_companies,
    list_companies as list_companies_query,
    save_company,
)
from app.features.companies.schemas.schema import (
    CompanyActivateResponse,
    CompanyCreatedResponse,
    CompanyListItem,
    CompanyOverviewItem,
    CompanyOverviewResponse,
    CompanyOverviewSummary,
    CompanyStats,
    CompanyStatisticsResponse,
    CompanySuspendResponse,
    CreateCompanyRequest,
)
from app.features.models import Company
from app.shared.enums.application_status import ApplicationStatus
from app.shared.schemas.response import PaginatedResponse


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")


async def create_company(db: AsyncSession, data: CreateCompanyRequest) -> CompanyCreatedResponse:
    company = await save_company(db, Company(name=data.name, slug=data.slug))
    await db.commit()
    return CompanyCreatedResponse(
        id=company.id,
        name=company.name,
        slug=company.slug,
        is_active=company.is_active,
    )


async def list_companies(
    db: AsyncSession,
    *,
    pagination: PaginationParams,
    q: str | None = None,
    is_active: bool | None = None,
) -> PaginatedResponse[CompanyListItem]:
    companies, total = await list_companies_query(
        db,
        pagination=pagination,
        q=q,
        is_active=is_active,
    )
    pages = (total + pagination.per_page - 1) // pagination.per_page
    return PaginatedResponse(
        data=[
            CompanyListItem(
                id=company.id,
                name=company.name,
                slug=company.slug,
                is_active=company.is_active,
                is_suspended=company.is_suspended,
                created_at=company.created_at.isoformat() if company.created_at else None,
            )
            for company in companies
        ],
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
        total_pages=pages,
        has_next=pagination.page < pages,
        has_prev=pagination.page > 1,
    )


async def suspend_company(db: AsyncSession, company_id: int) -> CompanySuspendResponse:
    company = await get_company_by_id(db, company_id)
    if not company:
        raise _not_found()
    company.is_suspended = True
    await db.commit()
    return CompanySuspendResponse(id=company.id, is_suspended=True)


async def activate_company(db: AsyncSession, company_id: int) -> CompanyActivateResponse:
    company = await get_company_by_id(db, company_id)
    if not company:
        raise _not_found()
    company.is_suspended = False
    company.is_active = True
    await db.commit()
    return CompanyActivateResponse(id=company.id, is_active=True, is_suspended=False)


async def get_company_statistics(db: AsyncSession, company_id: int) -> CompanyStatisticsResponse:
    company = await get_company_by_id(db, company_id)
    if not company:
        raise _not_found()
    return CompanyStatisticsResponse(
        company_id=company_id,
        company_name=company.name,
        is_active=company.is_active,
        is_suspended=company.is_suspended,
        stats=CompanyStats(
            total_jobs=await count_jobs(db, company_id),
            published_jobs=await count_jobs(db, company_id, published_only=True),
            total_applications=await count_applications(db, company_id=company_id),
            total_hired=await count_applications(db, company_id=company_id, status=ApplicationStatus.HIRED),
            total_rejected=await count_applications(db, company_id=company_id, status=ApplicationStatus.REJECTED),
            hr_users=await count_hr_users(db, company_id),
        ),
    )


async def get_multi_company_overview(db: AsyncSession) -> CompanyOverviewResponse:
    companies = await list_all_companies(db)
    summary_items = []
    for company in companies:
        summary_items.append(
            CompanyOverviewItem(
                id=company.id,
                name=company.name,
                slug=company.slug,
                is_active=company.is_active,
                is_suspended=company.is_suspended,
                total_jobs=await count_jobs(db, company.id),
                total_applications=await count_applications(db, company_id=company.id),
                created_at=company.created_at.isoformat() if company.created_at else None,
            )
        )

    return CompanyOverviewResponse(
        summary=CompanyOverviewSummary(
            total_companies=len(companies),
            active_companies=sum(1 for company in companies if company.is_active and not company.is_suspended),
            suspended_companies=sum(1 for company in companies if company.is_suspended),
            total_jobs_platform=await count_jobs(db),
            total_applications_platform=await count_applications(db),
        ),
        companies=summary_items,
    )
