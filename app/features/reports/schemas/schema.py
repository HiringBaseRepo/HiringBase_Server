from pydantic import BaseModel
from typing import List

class ChartDataItem(BaseModel):
    name: str
    value: float

class ReportStats(BaseModel):
    total_processed: int
    avg_match_rate: float
    screening_efficiency: float
    total_savings: float
    screening_data: List[ChartDataItem]
    match_distribution: List[ChartDataItem]
    company_activity: List[ChartDataItem]
