from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.reports.schemas.schema import ReportStats, ChartDataItem
from app.features.reports.repositories.repository import (
    get_screening_volume_stats,
    get_match_distribution_stats,
    get_company_activity_stats,
    get_report_summary_stats
)

async def get_report_stats(
    db: AsyncSession, 
    start_date: Optional[str] = None, 
    end_date: Optional[str] = None
) -> ReportStats:
    """Orchestrates report statistics data using real database values."""
    # Summary stats
    summary = await get_report_summary_stats(db)

    # Screening Volume Trend
    volume_raw = await get_screening_volume_stats(db)
    screening_data = [ChartDataItem(name=row[0], value=float(row[1])) for row in volume_raw]
    
    if not screening_data:
        for i in range(6, -1, -1):
            date_label = (datetime.now() - timedelta(days=i)).strftime('%b %d')
            screening_data.append(ChartDataItem(name=date_label, value=0.0))

    # Match Distribution
    distribution_raw = await get_match_distribution_stats(db)
    match_distribution = [ChartDataItem(name=row[0], value=float(row[1])) for row in distribution_raw]
    
    if not match_distribution:
        # Using 0.1 as a very small value so the PieChart segments at least exist in the DOM 
        # but look empty (or just use 0 if the chart handles it). 
        # Actually, let's stick to 0 but ensure all ranges are present.
        match_distribution = [
            ChartDataItem(name="90-100%", value=0.0),
            ChartDataItem(name="70-89%", value=0.0),
            ChartDataItem(name="50-69%", value=0.0),
            ChartDataItem(name="Below 50%", value=0.0),
        ]

    # Company Activity
    activity_raw = await get_company_activity_stats(db)
    company_activity = [ChartDataItem(name=row[0], value=float(row[1])) for row in activity_raw]
    
    if not company_activity:
        company_activity = [ChartDataItem(name="No Activity", value=0.0)]

    return ReportStats(
        total_processed=summary["total_processed"],
        avg_match_rate=summary["avg_match_rate"],
        screening_data=screening_data,
        match_distribution=match_distribution,
        company_activity=company_activity
    )
