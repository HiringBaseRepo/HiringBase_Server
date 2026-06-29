from pydantic import BaseModel
from typing import List, Optional

class ChartDataItem(BaseModel):
    name: str
    value: float

class BigDataOverview(BaseModel):
    total_jobs: int
    unique_companies: int
    keywords_tracked: int
    last_scrape_time: Optional[str] = None

class BigDataStats(BaseModel):
    top_keywords: List[ChartDataItem]
    keyword_distribution: List[ChartDataItem]
    category_distribution: List[ChartDataItem]
    job_type_distribution: List[ChartDataItem]
    top_companies: List[ChartDataItem]

class JobListItem(BaseModel):
    job_id: str
    title: str
    company: str
    category: str
    tags: List[str]
    job_type: str
    publication_date: Optional[str] = None
    candidate_required_location: Optional[str] = None
    salary: Optional[str] = None
    url: Optional[str] = None
    keyword: str
    scrape_time: str

class JobListResponse(BaseModel):
    items: List[JobListItem]
    total: int
    page: int
    page_size: int
    total_pages: int

class KeywordTrend(BaseModel):
    keyword: str
    data: List[ChartDataItem]

class RefreshResponse(BaseModel):
    triggered: bool
    message: str
