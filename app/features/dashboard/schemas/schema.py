from pydantic import BaseModel
from typing import List, Optional

class DashboardOverview(BaseModel):
    total_companies: int
    total_hr_users: int
    active_jobs: int
    total_applicants: str
    company_growth: str
    hr_growth: str
    job_status: str
    applicant_change: str

class RecentCampaign(BaseModel):
    id: int
    company_name: str
    company_initials: str
    job_title: str
    screened: int
    match_rate: int
    status: str
