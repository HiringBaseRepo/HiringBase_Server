from pydantic import BaseModel
from typing import List, Optional

class DashboardOverview(BaseModel):
    total_companies: int
    total_hr_users: int
    active_jobs: int
    system_health: float
    api_latency: int
    company_growth: str
    hr_growth: str
    job_status: str
    total_applicants: int
    applicant_change: str

class RecentCampaign(BaseModel):
    id: int
    company_name: str
    company_initials: str
    job_title: str
    screened: int
    match_rate: int
    status: str
