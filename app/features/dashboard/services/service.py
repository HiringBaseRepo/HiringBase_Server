from typing import List
import random
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.dashboard.schemas.schema import DashboardOverview, RecentCampaign
from app.features.dashboard.repositories.repository import (
    get_dashboard_stats,
    get_recent_jobs_with_counts,
    get_application_count_by_job
)
from app.shared.enums.job_status import JobStatus

async def get_dashboard_overview(db: AsyncSession) -> DashboardOverview:
    """Orchestrates dashboard overview data."""
    stats = await get_dashboard_stats(db)
    
    return DashboardOverview(
        total_companies=stats["total_companies"],
        total_hr_users=stats["total_hr_users"],
        active_jobs=stats["active_jobs"],
        system_health=99.8, # Mocked health percentage
        api_latency=random.randint(35, 55), # Mocked latency in ms
        company_growth="+12.5%", 
        hr_growth="+4.2%",      
        job_status="Stable",
        total_applicants=stats["total_applicants"],
        applicant_change="+8.1%"
    )

async def get_recent_campaigns(db: AsyncSession) -> List[RecentCampaign]:
    """Fetches and maps recent jobs as campaigns."""
    jobs = await get_recent_jobs_with_counts(db)
    
    campaigns = []
    for job in jobs:
        screened = await get_application_count_by_job(db, job.id)
        
        company_name = job.company.name if job.company and job.company.name else "Unknown"
        company_initials = "".join([n[0].upper() for n in company_name.split() if n])[:2] if company_name != "Unknown" else "UN"

        campaigns.append(RecentCampaign(
            id=job.id,
            company_name=company_name,
            company_initials=company_initials,
            job_title=job.title,
            screened=screened,
            match_rate=85, 
            status="active" if job.status == JobStatus.PUBLISHED else "completed"
        ))
    return campaigns
