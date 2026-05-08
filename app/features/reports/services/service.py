from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.reports.schemas.schema import ReportStats, ChartDataItem
from app.features.reports.repositories.repository import get_active_companies

async def get_report_stats(db: AsyncSession) -> ReportStats:
    """Orchestrates report statistics data."""
    # Screening Volume
    # TODO: Implement real trend calculation in repository
    screening_data = [
        ChartDataItem(name="Mon", value=450),
        ChartDataItem(name="Tue", value=520),
        ChartDataItem(name="Wed", value=480),
        ChartDataItem(name="Thu", value=610),
        ChartDataItem(name="Fri", value=580),
        ChartDataItem(name="Sat", value=200),
        ChartDataItem(name="Sun", value=150),
    ]

    # Match Distribution
    # TODO: Implement real score distribution in repository
    match_distribution = [
        ChartDataItem(name="90-100%", value=35),
        ChartDataItem(name="70-89%", value=45),
        ChartDataItem(name="50-69%", value=15),
        ChartDataItem(name="Below 50%", value=5),
    ]

    # Company Activity
    companies = await get_active_companies(db)
    
    company_activity = []
    for company in companies:
        # TODO: Implement real activity volume calculation in repository
        company_activity.append(ChartDataItem(name=company.name[:10], value=100 + (company.id % 50)))
        
    return ReportStats(
        screening_data=screening_data,
        match_distribution=match_distribution,
        company_activity=company_activity
    )
