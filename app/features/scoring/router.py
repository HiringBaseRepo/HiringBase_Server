"""Dynamic Scoring Template API."""
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database.base import get_db
from app.features.auth.dependencies import require_hr
from app.features.models import JobScoringTemplate, Job
from app.shared.schemas.response import StandardResponse
from app.core.config import settings

router = APIRouter(prefix="/scoring", tags=["Scoring Templates"])


@router.post("/templates", response_model=StandardResponse[dict])
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
    total = skill_match_weight + experience_weight + education_weight + portfolio_weight + soft_skill_weight + administrative_weight
    if total != 100:
        return StandardResponse.error(message=f"Weights must sum to 100, got {total}")

    # Delete existing template if any
    existing = await db.execute(select(JobScoringTemplate).where(JobScoringTemplate.job_id == job_id))
    old = existing.scalar_one_or_none()
    if old:
        await db.delete(old)

    tpl = JobScoringTemplate(
        job_id=job_id,
        skill_match_weight=skill_match_weight,
        experience_weight=experience_weight,
        education_weight=education_weight,
        portfolio_weight=portfolio_weight,
        soft_skill_weight=soft_skill_weight,
        administrative_weight=administrative_weight,
        custom_rules=custom_rules,
    )
    db.add(tpl)
    await db.commit()
    await db.refresh(tpl)
    return StandardResponse.ok(data={"template_id": tpl.id, "job_id": job_id})


@router.patch("/templates/{template_id}", response_model=StandardResponse[dict])
async def update_scoring_template(
    template_id: int,
    updates: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_hr),
):
    result = await db.execute(select(JobScoringTemplate).where(JobScoringTemplate.id == template_id))
    tpl = result.scalar_one_or_none()
    if not tpl:
        return StandardResponse.error(message="Template not found", status_code=404)
    for key, value in updates.items():
        if hasattr(tpl, key):
            setattr(tpl, key, value)
    await db.commit()
    return StandardResponse.ok(data={"template_id": tpl.id, "updated": True})


@router.get("/templates/{job_id}", response_model=StandardResponse[dict])
async def get_scoring_template(job_id: int, db: AsyncSession = Depends(get_db), current_user=Depends(require_hr)):
    result = await db.execute(select(JobScoringTemplate).where(JobScoringTemplate.job_id == job_id))
    tpl = result.scalar_one_or_none()
    if not tpl:
        return StandardResponse.error(message="Template not found", status_code=404)
    return StandardResponse.ok(data={
        "template_id": tpl.id,
        "weights": {
            "skill_match": tpl.skill_match_weight,
            "experience": tpl.experience_weight,
            "education": tpl.education_weight,
            "portfolio": tpl.portfolio_weight,
            "soft_skill": tpl.soft_skill_weight,
            "administrative": tpl.administrative_weight,
        },
        "custom_rules": tpl.custom_rules,
    })
