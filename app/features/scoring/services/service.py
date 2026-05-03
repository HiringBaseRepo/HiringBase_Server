"""Scoring template business logic."""
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.models import JobScoringTemplate
from app.features.scoring.repositories.repository import (
    delete_template,
    get_template_by_id,
    get_template_by_job_id,
    save_template,
)
from app.features.scoring.schemas.schema import (
    CreateScoringTemplateRequest,
    ScoringTemplateCreatedResponse,
    ScoringTemplateResponse,
    ScoringTemplateUpdateResponse,
    ScoringWeightsResponse,
)


def _validate_weight_total(data: CreateScoringTemplateRequest) -> None:
    total = (
        data.skill_match_weight
        + data.experience_weight
        + data.education_weight
        + data.portfolio_weight
        + data.soft_skill_weight
        + data.administrative_weight
    )
    if total != 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Weights must sum to 100, got {total}",
        )


async def create_scoring_template(
    db: AsyncSession,
    data: CreateScoringTemplateRequest,
) -> ScoringTemplateCreatedResponse:
    _validate_weight_total(data)
    old = await get_template_by_job_id(db, data.job_id)
    if old:
        await delete_template(db, old)

    template = JobScoringTemplate(
        job_id=data.job_id,
        skill_match_weight=data.skill_match_weight,
        experience_weight=data.experience_weight,
        education_weight=data.education_weight,
        portfolio_weight=data.portfolio_weight,
        soft_skill_weight=data.soft_skill_weight,
        administrative_weight=data.administrative_weight,
        custom_rules=data.custom_rules,
    )
    template = await save_template(db, template)
    await db.commit()
    return ScoringTemplateCreatedResponse(template_id=template.id, job_id=data.job_id)


async def update_scoring_template(
    db: AsyncSession,
    *,
    template_id: int,
    updates: dict,
) -> ScoringTemplateUpdateResponse:
    template = await get_template_by_id(db, template_id)
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    for key, value in updates.items():
        if hasattr(template, key):
            setattr(template, key, value)
    await db.commit()
    return ScoringTemplateUpdateResponse(template_id=template.id, updated=True)


async def get_scoring_template(db: AsyncSession, job_id: int) -> ScoringTemplateResponse:
    template = await get_template_by_job_id(db, job_id)
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return ScoringTemplateResponse(
        template_id=template.id,
        weights=ScoringWeightsResponse(
            skill_match=template.skill_match_weight,
            experience=template.experience_weight,
            education=template.education_weight,
            portfolio=template.portfolio_weight,
            soft_skill=template.soft_skill_weight,
            administrative=template.administrative_weight,
        ),
        custom_rules=template.custom_rules,
    )
