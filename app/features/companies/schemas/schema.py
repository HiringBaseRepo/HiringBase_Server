"""Company management schemas."""
from pydantic import BaseModel


class CreateCompanyRequest(BaseModel):
    name: str
    slug: str


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
