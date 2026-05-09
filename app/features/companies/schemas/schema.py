"""Company management schemas."""
from pydantic import BaseModel


class CreateCompanyRequest(BaseModel):
    name: str | None = None
    slug: str | None = None
    industry: str | None = None
    website: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    quota: str | None = None
    model: str | None = None
    auto_onboarding: bool = True
    logo_url: str | None = None


class CompanyDetailResponse(BaseModel):
    id: int
    name: str
    slug: str
    industry: str | None
    website: str | None
    description: str | None
    is_active: bool
    is_suspended: bool
    logo_url: str | None
    contact_name: str | None
    contact_email: str | None
    contact_phone: str | None
    created_at: str | None


class CompanyCreatedResponse(BaseModel):
    id: int
    name: str
    slug: str
    is_active: bool


class CompanyListItem(BaseModel):
    id: int
    name: str
    slug: str
    is_active: bool
    is_suspended: bool
    industry: str | None = None
    hr_count: int = 0
    logo_url: str | None = None
    created_at: str | None


class CompanySuspendResponse(BaseModel):
    id: int
    is_suspended: bool


class CompanyActivateResponse(BaseModel):
    id: int
    is_active: bool
    is_suspended: bool


class CompanyStats(BaseModel):
    total_jobs: int
    published_jobs: int
    total_applications: int
    total_hired: int
    total_rejected: int
    hr_users: int


class CompanyStatisticsResponse(BaseModel):
    company_id: int
    company_name: str
    is_active: bool
    is_suspended: bool
    stats: CompanyStats


class CompanyOverviewSummary(BaseModel):
    total_companies: int
    active_companies: int
    suspended_companies: int
    total_jobs_platform: int
    total_applications_platform: int


class CompanyOverviewItem(BaseModel):
    id: int
    name: str
    slug: str
    is_active: bool
    is_suspended: bool
    total_jobs: int
    total_applications: int
    created_at: str | None


class CompanyOverviewResponse(BaseModel):
    summary: CompanyOverviewSummary
    companies: list[CompanyOverviewItem]
