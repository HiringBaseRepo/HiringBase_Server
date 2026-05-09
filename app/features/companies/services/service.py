"""Company management business logic."""
from app.core.exceptions import CompanyNotFoundException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils.pagination import PaginationParams
from app.features.companies.repositories.repository import (
    count_applications,
    count_hr_users,
    count_jobs,
    get_company_by_id as get_company_repository_id,
    list_all_companies,
    save_company,
    update_company_repo,
    get_hr_contact,
    list_companies as list_companies_query,
)
from app.features.users.models import User as DBUser
from app.features.users.repositories.repository import save_user, update_user_repo
from app.shared.enums.user_roles import UserRole
from fastapi import UploadFile
from app.shared.helpers.storage import generate_filename, build_public_url, get_s3_client
from app.core.config import settings
from app.features.companies.schemas.schema import (
    CompanyActivateResponse,
    CompanyCreatedResponse,
    CompanyDetailResponse,
    CompanyListItem,
    CompanyOverviewItem,
    CompanyOverviewResponse,
    CompanyOverviewSummary,
    CompanyStats,
    CompanyStatisticsResponse,
    CompanySuspendResponse,
    CreateCompanyRequest,
)
from app.features.audit_logs.models import AuditLog
from app.features.audit_logs.repositories.repository import create_audit_log
from app.features.companies.models import Company
from app.shared.enums.application_status import ApplicationStatus
from app.shared.schemas.response import PaginatedResponse


async def create_company(db: AsyncSession, data: CreateCompanyRequest) -> CompanyCreatedResponse:
    slug = data.slug
    if not slug:
        # Simple slugify
        slug = data.name.lower().replace(" ", "-")
        import re
        slug = re.sub(r'[^a-z0-9-]', '', slug)
    
    # We might need to check if slug exists, but for now let's just create it
    company = Company(
        name=data.name,
        slug=slug,
        industry=data.industry,
        website=data.website,
        logo_url=data.logo_url,
        description=f"Contact: {data.contact_name} ({data.contact_email})",
    )
    company = await save_company(db, company)

    # Create HR User
    hr_user = DBUser(
        company_id=company.id,
        email=data.contact_email,
        full_name=data.contact_name,
        phone=data.contact_phone,
        role=UserRole.HR,
        is_active=True,
    )
    await save_user(db, hr_user)
    
    await db.commit()
    return CompanyCreatedResponse(
        id=company.id,
        name=company.name,
        slug=company.slug,
        is_active=company.is_active,
    )


async def get_company_by_id(db: AsyncSession, company_id: int) -> CompanyDetailResponse:
    company = await get_company_repository_id(db, company_id)
    if not company:
        raise CompanyNotFoundException()

    hr_contact = await get_hr_contact(db, company_id)
    return CompanyDetailResponse(
        id=company.id,
        name=company.name,
        slug=company.slug,
        industry=company.industry,
        website=company.website,
        description=company.description,
        is_active=company.is_active,
        is_suspended=company.is_suspended,
        logo_url=company.logo_url,
        contact_name=hr_contact.full_name if hr_contact else None,
        contact_email=hr_contact.email if hr_contact else None,
        contact_phone=hr_contact.phone if hr_contact else None,
        created_at=company.created_at.isoformat() if company.created_at else None,
    )


async def upload_logo(db: AsyncSession, file: UploadFile) -> str:
    content = await file.read()
    key = generate_filename(file.filename, "company-logos")
    s3 = get_s3_client()
    s3.put_object(
        Bucket=settings.R2_BUCKET_NAME,
        Key=key,
        Body=content,
        ContentType=file.content_type or "image/png",
    )
    return build_public_url(key)


async def update_company(
    db: AsyncSession, company_id: int, data: CreateCompanyRequest
) -> CompanyDetailResponse:
    company = await get_company_repository_id(db, company_id)
    if not company:
        raise CompanyNotFoundException()

    if data.name is not None:
        company.name = data.name
    if data.industry is not None:
        company.industry = data.industry
    if data.website is not None:
        company.website = data.website
    if data.logo_url is not None:
        company.logo_url = data.logo_url
    
    await update_company_repo(db, company)

    # Update HR Contact User
    hr_contact = await get_hr_contact(db, company_id)
    if hr_contact:
        if data.contact_name:
            hr_contact.full_name = data.contact_name
        if data.contact_email:
            hr_contact.email = data.contact_email
        if data.contact_phone:
            hr_contact.phone = data.contact_phone
        await update_user_repo(db, hr_contact)
    else:
        # Create HR user if it doesn't exist (for older companies)
        new_hr = DBUser(
            company_id=company_id,
            email=data.contact_email or f"admin@{company.slug}.com",
            full_name=data.contact_name or company.name,
            phone=data.contact_phone,
            role=UserRole.HR,
            is_active=True,
        )
        await save_user(db, new_hr)

    await db.commit()

    return await get_company_by_id(db, company_id)


async def list_companies(
    db: AsyncSession,
    *,
    pagination: PaginationParams,
    q: str | None = None,
    industry: str | None = None,
    is_active: bool | None = None,
) -> PaginatedResponse[CompanyListItem]:
    companies, total = await list_companies_query(
        db,
        pagination=pagination,
        q=q,
        industry=industry,
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
                industry=company.industry,
                hr_count=await count_hr_users(db, company.id),
                logo_url=company.logo_url,
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
        raise CompanyNotFoundException()
    company.is_suspended = True
    await create_audit_log(
        db,
        AuditLog(
            company_id=company.id,
            user_id=None,  # System or Admin (depends on current_user, but this service doesn't receive it yet)
            action="COMPANY_SUSPEND",
            entity_type="company",
            entity_id=company.id,
            new_values={"is_suspended": True},
        ),
    )
    await db.commit()
    return CompanySuspendResponse(id=company.id, is_suspended=True)


async def activate_company(db: AsyncSession, company_id: int) -> CompanyActivateResponse:
    company = await get_company_by_id(db, company_id)
    if not company:
        raise CompanyNotFoundException()
    company.is_suspended = False
    company.is_active = True
    await create_audit_log(
        db,
        AuditLog(
            company_id=company.id,
            user_id=None,
            action="COMPANY_ACTIVATE",
            entity_type="company",
            entity_id=company.id,
            new_values={"is_active": True, "is_suspended": False},
        ),
    )
    await db.commit()
    return CompanyActivateResponse(id=company.id, is_active=True, is_suspended=False)


async def get_company_statistics(db: AsyncSession, company_id: int) -> CompanyStatisticsResponse:
    company = await get_company_by_id(db, company_id)
    if not company:
        raise CompanyNotFoundException()
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
