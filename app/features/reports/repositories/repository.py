from typing import List, Tuple
from sqlalchemy import select, func, case, desc, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.companies.models import Company
from app.features.applications.models import Application
from app.features.screening.models import CandidateScore
from app.features.jobs.models import Job

async def get_screening_volume_stats(db: AsyncSession, days: int = 7) -> List[Tuple[str, int]]:
    """Get count of applications grouped by day."""
    # Using a subquery or a simpler group by to avoid PostgreSQL grouping errors
    stmt = (
        select(
            func.to_char(Application.created_at, 'Mon DD').label('date_label'),
            func.count(Application.id).label('count'),
            func.min(Application.created_at).label('sort_key')
        )
        .where(Application.deleted_at.is_(None))
        .group_by(text('date_label'))
        .order_by(desc('sort_key'))
        .limit(days)
    )
    result = await db.execute(stmt)
    return [(row[0], row[1]) for row in result.all()]

async def get_match_distribution_stats(db: AsyncSession) -> List[Tuple[str, int]]:
    """Get distribution of match scores."""
    stmt = select(
        case(
            (CandidateScore.final_score >= 90, "90-100%"),
            (CandidateScore.final_score >= 70, "70-89%"),
            (CandidateScore.final_score >= 50, "50-69%"),
            else_="Below 50%"
        ).label('range'),
        func.count(CandidateScore.id).label('count')
    ).group_by(text('range'))
    
    result = await db.execute(stmt)
    return result.all()

async def get_company_activity_stats(db: AsyncSession, limit: int = 5) -> List[Tuple[str, int]]:
    """Get application counts grouped by company."""
    stmt = (
        select(Company.name, func.count(Application.id))
        .join(Job, Job.company_id == Company.id)
        .join(Application, Application.job_id == Job.id)
        .where(Company.deleted_at.is_(None))
        .group_by(Company.name)
        .order_by(desc(func.count(Application.id)))
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.all()

async def get_report_summary_stats(db: AsyncSession) -> dict:
    """Get aggregate statistics for the summary bar."""
    # Total Processed
    total_processed_stmt = select(func.count(Application.id)).where(Application.deleted_at.is_(None))
    total_processed = (await db.execute(total_processed_stmt)).scalar_one()

    # Avg Match Rate
    avg_match_stmt = select(func.avg(CandidateScore.final_score)).where(CandidateScore.final_score > 0)
    avg_match_rate = (await db.execute(avg_match_stmt)).scalar() or 0.0

    return {
        "total_processed": total_processed,
        "avg_match_rate": round(float(avg_match_rate), 1),
    }
