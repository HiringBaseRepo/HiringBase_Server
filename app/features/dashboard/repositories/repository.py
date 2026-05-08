from typing import List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.companies.models import Company
from app.features.users.models import User
from app.features.jobs.models import Job
from app.features.applications.models import Application
from app.shared.enums.user_roles import UserRole
from app.shared.enums.job_status import JobStatus

async def get_dashboard_stats(db: AsyncSession) -> dict:
    """Get core counts for dashboard."""
    # Total Companies
    total_companies_stmt = select(func.count(Company.id)).where(Company.deleted_at.is_(None))
    total_companies = (await db.execute(total_companies_stmt)).scalar_one()

    # Total HR Users
    total_hr_users_stmt = select(func.count(User.id)).where(User.role == UserRole.HR, User.deleted_at.is_(None))
    total_hr_users = (await db.execute(total_hr_users_stmt)).scalar_one()

    # Active Jobs
    active_jobs_stmt = select(func.count(Job.id)).where(Job.status == JobStatus.PUBLISHED, Job.deleted_at.is_(None))
    active_jobs = (await db.execute(active_jobs_stmt)).scalar_one()

    # Total Applicants
    total_applicants_stmt = select(func.count(Application.id)).where(Application.deleted_at.is_(None))
    total_applicants = (await db.execute(total_applicants_stmt)).scalar_one()

    return {
        "total_companies": total_companies,
        "total_hr_users": total_hr_users,
        "active_jobs": active_jobs,
        "total_applicants": total_applicants
    }

async def get_recent_jobs_with_counts(db: AsyncSession, limit: int = 5) -> List[Job]:
    """Fetch recent jobs with their basic relations."""
    stmt = (
        select(Job)
        .where(Job.deleted_at.is_(None))
        .order_by(Job.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()

async def get_application_count_by_job(db: AsyncSession, job_id: int) -> int:
    """Get total application count for a specific job."""
    apps_stmt = select(func.count(Application.id)).where(Application.job_id == job_id)
    return (await db.execute(apps_stmt)).scalar_one()
