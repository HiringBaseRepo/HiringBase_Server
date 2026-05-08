from pydantic import BaseModel
from typing import List, Any

class ChartDataItem(BaseModel):
    name: str
    value: float

class ReportStats(BaseModel):
    screening_data: List[ChartDataItem]
    match_distribution: List[ChartDataItem]
    company_activity: List[ChartDataItem]
