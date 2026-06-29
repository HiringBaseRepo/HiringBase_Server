from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
import structlog
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.features.big_data.schemas.schema import (
    BigDataOverview,
    BigDataStats,
    ChartDataItem,
    JobListItem,
    JobListResponse,
    KeywordTrend
)

logger = structlog.get_logger()

_COLLECTION = "jobs"

async def get_overview(db: Optional[AsyncIOMotorDatabase]) -> BigDataOverview:
    """
    Get general overview of scraped jobs: total counts, unique companies, keywords.
    """
    if db is None:
        return BigDataOverview(total_jobs=0, unique_companies=0, keywords_tracked=0, last_scrape_time=None)
        
    try:
        coll = db[_COLLECTION]
        
        # 1. Total jobs
        total_jobs = await coll.count_documents({})
        
        # 2. Unique companies
        pipeline_companies = [{"$group": {"_id": "$company"}}, {"$count": "count"}]
        res_companies = await coll.aggregate(pipeline_companies).to_list(length=1)
        unique_companies = res_companies[0]["count"] if res_companies else 0
        
        # 3. Unique keywords
        pipeline_keywords = [{"$group": {"_id": "$keyword"}}, {"$count": "count"}]
        res_keywords = await coll.aggregate(pipeline_keywords).to_list(length=1)
        keywords_tracked = res_keywords[0]["count"] if res_keywords else 0
        
        # 4. Last scrape time
        last_job = await coll.find({}, {"scrape_time": 1}).sort("scrape_time", -1).limit(1).to_list(length=1)
        last_scrape_time = last_job[0].get("scrape_time") if last_job else None
        
        return BigDataOverview(
            total_jobs=total_jobs,
            unique_companies=unique_companies,
            keywords_tracked=keywords_tracked,
            last_scrape_time=last_scrape_time
        )
    except Exception as e:
        logger.error("mongo_repo_get_overview_failed", error=str(e))
        return BigDataOverview(total_jobs=0, unique_companies=0, keywords_tracked=0, last_scrape_time=None)

async def get_stats(db: Optional[AsyncIOMotorDatabase]) -> BigDataStats:
    """
    Get aggregate counts for charts.
    """
    default_stats = BigDataStats(
        top_keywords=[],
        keyword_distribution=[],
        category_distribution=[],
        job_type_distribution=[],
        top_companies=[]
    )
    
    if db is None:
        return default_stats
        
    try:
        coll = db[_COLLECTION]
        
        # Helper for basic grouping aggregation
        async def run_group_agg(field: str, limit: int = 10) -> List[ChartDataItem]:
            pipeline = [
                {"$group": {"_id": f"${field}", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": limit}
            ]
            res = await coll.aggregate(pipeline).to_list(length=limit)
            return [
                ChartDataItem(name=str(row["_id"]) if row["_id"] else "Unknown", value=float(row["count"]))
                for row in res
            ]
            
        top_keywords = await run_group_agg("keyword", 15)
        category_distribution = await run_group_agg("category", 10)
        job_type_distribution = await run_group_agg("job_type", 10)
        top_companies = await run_group_agg("company", 5)
        
        return BigDataStats(
            top_keywords=top_keywords,
            keyword_distribution=top_keywords, # Map same for distribution for flexibility
            category_distribution=category_distribution,
            job_type_distribution=job_type_distribution,
            top_companies=top_companies
        )
    except Exception as e:
        logger.error("mongo_repo_get_stats_failed", error=str(e))
        return default_stats

async def get_jobs(
    db: Optional[AsyncIOMotorDatabase],
    search: Optional[str] = None,
    keyword: Optional[str] = None,
    category: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "publication_date",
    sort_dir: str = "desc"
) -> JobListResponse:
    """
    Fetch paginated job list matching criteria.
    """
    default_response = JobListResponse(items=[], total=0, page=page, page_size=page_size, total_pages=0)
    if db is None:
        return default_response
        
    try:
        coll = db[_COLLECTION]
        
        # 1. Build Query Filter
        query: Dict[str, Any] = {}
        if search:
            query["$or"] = [
                {"title": {"$regex": search, "$options": "i"}},
                {"company": {"$regex": search, "$options": "i"}}
            ]
        if keyword:
            query["keyword"] = keyword
        if category:
            query["category"] = category
            
        # 2. Get total matching count
        total = await coll.count_documents(query)
        if total == 0:
            return default_response
            
        # 3. Pagination calculation
        skip = (page - 1) * page_size
        total_pages = (total + page_size - 1) // page_size
        
        # 4. Sorting mapping
        direction = -1 if sort_dir.lower() == "desc" else 1
        # Default safety fallback
        sort_field = sort_by if sort_by in ["publication_date", "scrape_time", "title", "company"] else "publication_date"
        
        cursor = coll.find(query).sort(sort_field, direction).skip(skip).limit(page_size)
        raw_items = await cursor.to_list(length=page_size)
        
        items = []
        for doc in raw_items:
            # Map Mongo document to schema, ensuring no _id leak
            items.append(JobListItem(
                job_id=str(doc.get("job_id", "")),
                title=doc.get("title", ""),
                company=doc.get("company", ""),
                category=doc.get("category", ""),
                tags=doc.get("tags", []),
                job_type=doc.get("job_type", ""),
                publication_date=doc.get("publication_date"),
                candidate_required_location=doc.get("candidate_required_location"),
                salary=doc.get("salary"),
                url=doc.get("url"),
                keyword=doc.get("keyword", ""),
                scrape_time=doc.get("scrape_time", "")
            ))
            
        return JobListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    except Exception as e:
        logger.error("mongo_repo_get_jobs_failed", error=str(e))
        return default_response

async def get_trends(db: Optional[AsyncIOMotorDatabase], days: int = 30) -> List[KeywordTrend]:
    """
    Calculate keyword volume trends over the past X days.
    """
    if db is None:
        return []
        
    try:
        coll = db[_COLLECTION]
        
        # We aggregate over jobs published/scraped in the last X days.
        # Group by keyword and the date part of publication_date (YYYY-MM-DD).
        start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        pipeline = [
            # Filter recent records (remotive dates are usually strings starting with YYYY-MM-DD)
            {"$match": {"publication_date": {"$gte": start_date}}},
            # Group by keyword and day
            {
                "$group": {
                    "_id": {
                        "keyword": "$keyword",
                        "date": {"$substr": ["$publication_date", 0, 10]}
                    },
                    "count": {"$sum": 1}
                }
            },
            # Sort by date ascending
            {"$sort": {"_id.date": 1}}
        ]
        
        res = await coll.aggregate(pipeline).to_list(length=1000)
        
        # Organize data by keyword
        keyword_data_map: Dict[str, Dict[str, float]] = {}
        
        # Prefill last 30 days for each keyword to prevent empty charts/missing dates
        all_dates = [(datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days-1, -1, -1)]
        
        for row in res:
            keyword = row["_id"]["keyword"]
            date_str = row["_id"]["date"]
            count = row["count"]
            
            if not keyword or not date_str:
                continue
                
            if keyword not in keyword_data_map:
                # Initialize with 0s for all dates
                keyword_data_map[keyword] = {d: 0.0 for d in all_dates}
                
            # If the date falls inside our trend range, save it
            if date_str in keyword_data_map[keyword]:
                keyword_data_map[keyword][date_str] = float(count)
                
        # Format response
        trends = []
        for keyword, dates_dict in keyword_data_map.items():
            data_items = [ChartDataItem(name=d, value=v) for d, v in dates_dict.items()]
            trends.append(KeywordTrend(keyword=keyword, data=data_items))
            
        return trends
    except Exception as e:
        logger.error("mongo_repo_get_trends_failed", error=str(e))
        return []
