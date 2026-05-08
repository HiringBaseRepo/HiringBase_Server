from typing import List
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
    
    total_applicants = stats["total_applicants"]
    
    return DashboardOverview(
        total_companies=stats["total_companies"],
        total_hr_users=stats["total_hr_users"],
        active_jobs=stats["active_jobs"],
        total_applicants=f"{total_applicants/1000:.1f}k" if total_applicants >= 1000 else str(total_applicants),
        # TODO: Implement real growth calculation logic in repository
        company_growth="+12.5%", 
        hr_growth="+4.2%",      
        job_status="Stable",    
        applicant_change="-2.1%" 
    )

async def get_recent_campaigns(db: AsyncSession) -> List[RecentCampaign]:
    """Fetches and maps recent jobs as campaigns."""
    jobs = await get_recent_jobs_with_counts(db)
    
    campaigns = []
    for job in jobs:
        screened = await get_application_count_by_job(db, job.id)
        
        campaigns.append(RecentCampaign(
            id=job.id,
            company_name=job.company.name if job.company else "Unknown",
            company_initials="".join([n[0] for n in job.company.name.split()]) if job.company and job.company.name else "UN",
            job_title=job.title,
            screened=screened,
            # TODO: Implement real match rate calculation based on application scores
            match_rate=85, 
            status="active" if job.status == JobStatus.PUBLISHED else "completed"
        ))
    return campaigns
