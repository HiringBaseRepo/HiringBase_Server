from typing import List
import time
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.dashboard.schemas.schema import DashboardOverview, RecentCampaign
from app.features.dashboard.repositories.repository import (
    get_dashboard_stats,
    get_recent_jobs_with_counts,
    get_application_count_by_job
)
from app.shared.enums.job_status import JobStatus

async def get_dashboard_overview(db: AsyncSession) -> DashboardOverview:
    """Orchestrates dashboard overview data with real health checks."""
    # Start timer for latency measurement
    start_time = time.perf_counter()
    
    try:
        # Core stats from DB
        stats = await get_dashboard_stats(db)
        
        # Real DB health check (Ping)
        from app.features.dashboard.repositories.repository import ping_database
        await ping_database(db)
        system_health = 100.0
    except Exception:
        # If DB connection or stats fetch fails
        stats = {
            "total_companies": 0,
            "total_hr_users": 0,
            "active_jobs": 0,
            "total_applicants": 0
        }
        system_health = 0.0
    
    # Calculate execution latency in ms
    execution_time_ms = int((time.perf_counter() - start_time) * 1000)
    
    return DashboardOverview(
        total_companies=stats["total_companies"],
        total_hr_users=stats["total_hr_users"],
        active_jobs=stats["active_jobs"],
        system_health=system_health,
        api_latency=execution_time_ms,
        company_growth="", # Cleared until real logic implemented
        hr_growth="",      
        job_status="Healthy" if system_health > 0 else "Down",
        total_applicants=stats["total_applicants"],
        applicant_change=""
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
