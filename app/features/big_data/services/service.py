from typing import List, Optional
import httpx
import structlog
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import settings
from app.features.big_data.schemas.schema import (
    BigDataOverview,
    BigDataStats,
    JobListResponse,
    KeywordTrend,
    RefreshResponse
)
from app.features.big_data.repositories import repository as repo

logger = structlog.get_logger()

async def get_big_data_overview(db: Optional[AsyncIOMotorDatabase]) -> BigDataOverview:
    return await repo.get_overview(db)

async def get_big_data_stats(db: Optional[AsyncIOMotorDatabase]) -> BigDataStats:
    return await repo.get_stats(db)

async def get_big_data_jobs(
    db: Optional[AsyncIOMotorDatabase],
    search: Optional[str] = None,
    keyword: Optional[str] = None,
    category: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "publication_date",
    sort_dir: str = "desc"
) -> JobListResponse:
    return await repo.get_jobs(
        db, search=search, keyword=keyword, category=category,
        page=page, page_size=page_size, sort_by=sort_by, sort_dir=sort_dir
    )

async def get_big_data_trends(db: Optional[AsyncIOMotorDatabase], days: int = 30) -> List[KeywordTrend]:
    return await repo.get_trends(db, days=days)

async def trigger_scraper_refresh() -> RefreshResponse:
    """
    Trigger manual scraper job in GitHub Actions via workflow_dispatch API.
    """
    pat = settings.SCRAPER_PAT
    repo_name = settings.GITHUB_REPO
    
    if not pat or not repo_name:
        logger.warn(
            "github_refresh_missing_credentials",
            has_pat=bool(pat),
            has_repo=bool(repo_name),
            message="GitHub PAT or repository config not found. Manual refresh is disabled."
        )
        return RefreshResponse(
            triggered=False,
            message="Manual refresh is unavailable: GitHub credentials or target repository not configured on the server."
        )
        
    url = f"https://api.github.com/repos/{repo_name}/actions/workflows/scrape-jobs.yml/dispatches"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {pat}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "HiringBase-Backend-API"
    }
    # Dispatch on default branch (main/master)
    payload = {"ref": "main"}
    
    logger.info("triggering_github_workflow_dispatch", repo=repo_name, url=url)
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            
            if response.status_code == 204:
                logger.info("github_workflow_dispatch_success", repo=repo_name)
                return RefreshResponse(
                    triggered=True,
                    message="Scraper job successfully dispatched via GitHub Actions."
                )
            else:
                logger.error(
                    "github_workflow_dispatch_failed",
                    status_code=response.status_code,
                    response_text=response.text
                )
                return RefreshResponse(
                    triggered=False,
                    message=f"GitHub API returned error status: {response.status_code}. Unable to launch scraper."
                )
    except Exception as e:
        logger.error("github_workflow_dispatch_exception", error=str(e))
        return RefreshResponse(
            triggered=False,
            message=f"Network error occurred while calling GitHub API: {str(e)}"
        )
