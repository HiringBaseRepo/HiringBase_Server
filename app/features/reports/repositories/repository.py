from typing import List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.companies.models import Company

async def get_active_companies(db: AsyncSession, limit: int = 5) -> List[Company]:
    """Fetch active companies for report listing."""
    stmt = select(Company).where(Company.deleted_at.is_(None)).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()

# TODO: Add functions for:
# - get_screening_volume_stats(db, start_date, end_date)
# - get_match_distribution_stats(db)
# - get_company_activity_stats(db)
