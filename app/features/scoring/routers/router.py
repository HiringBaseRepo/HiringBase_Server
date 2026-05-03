"""Dynamic Scoring Template API."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.base import get_db
from app.features.auth.dependencies.auth import require_hr
from app.features.scoring.schemas.schema import (
    CreateScoringTemplateRequest,
    ScoringTemplateCreatedResponse,
    ScoringTemplateResponse,
    ScoringTemplateUpdateResponse,
)
from app.features.scoring.services.service import (
    create_scoring_template as create_scoring_template_service,
    get_scoring_template as get_scoring_template_service,
    update_scoring_template as update_scoring_template_service,
)
from app.shared.schemas.response import StandardResponse
from app.core.config import settings

router = APIRouter(prefix="/scoring", tags=["Scoring Templates"])


@router.post("/templates", response_model=StandardResponse[ScoringTemplateCreatedResponse])
async def create_scoring_template(
    job_id: int,
    skill_match_weight: int = settings.DEFAULT_SKILL_WEIGHT,
    experience_weight: int = settings.DEFAULT_EXPERIENCE_WEIGHT,
    education_weight: int = settings.DEFAULT_EDUCATION_WEIGHT,
    portfolio_weight: int = settings.DEFAULT_PORTFOLIO_WEIGHT,
    soft_skill_weight: int = settings.DEFAULT_SOFT_SKILL_WEIGHT,
    administrative_weight: int = settings.DEFAULT_ADMIN_WEIGHT,
    custom_rules: Optional[dict] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_hr),
):
    data = CreateScoringTemplateRequest(
        job_id=job_id,
        skill_match_weight=skill_match_weight,
        experience_weight=experience_weight,
        education_weight=education_weight,
        portfolio_weight=portfolio_weight,
        soft_skill_weight=soft_skill_weight,
        administrative_weight=administrative_weight,
        custom_rules=custom_rules,
    )
    result = await create_scoring_template_service(db, data)
    return StandardResponse.ok(data=result)


@router.patch("/templates/{template_id}", response_model=StandardResponse[ScoringTemplateUpdateResponse])
async def update_scoring_template(
    template_id: int,
    updates: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_hr),
):
    result = await update_scoring_template_service(db, template_id=template_id, updates=updates)
    return StandardResponse.ok(data=result)


@router.get("/templates/{job_id}", response_model=StandardResponse[ScoringTemplateResponse])
async def get_scoring_template(job_id: int, db: AsyncSession = Depends(get_db), current_user=Depends(require_hr)):
    result = await get_scoring_template_service(db, job_id)
    return StandardResponse.ok(data=result)
