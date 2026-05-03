"""HR Manual Override API."""
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database.base import get_db
from app.features.auth.dependencies.auth import require_hr
from app.features.models import CandidateScore, Application, Job, AuditLog
from app.shared.schemas.response import StandardResponse

router = APIRouter(prefix="/manual-override", tags=["Manual Override"])


@router.post("/{application_id}", response_model=StandardResponse[dict])
async def manual_override_score(
    application_id: int,
    skill_adjustment: float = 0.0,
    experience_adjustment: float = 0.0,
    education_adjustment: float = 0.0,
    portfolio_adjustment: float = 0.0,
    soft_skill_adjustment: float = 0.0,
    admin_adjustment: float = 0.0,
    reason: str = "",
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_hr),
):
    result = await db.execute(select(CandidateScore).join(Application).join(Job).where(
        Application.id == application_id,
        Job.company_id == current_user.company_id,
    ))
    score = result.scalar_one_or_none()
    if not score:
        return StandardResponse.error(message="Score not found", status_code=404)

    old_final = score.final_score

    score.skill_match_score = max(0, min(100, score.skill_match_score + skill_adjustment))
    score.experience_score = max(0, min(100, score.experience_score + experience_adjustment))
    score.education_score = max(0, min(100, score.education_score + education_adjustment))
    score.portfolio_score = max(0, min(100, score.portfolio_score + portfolio_adjustment))
    score.soft_skill_score = max(0, min(100, score.soft_skill_score + soft_skill_adjustment))
    score.administrative_score = max(0, min(100, score.administrative_score + admin_adjustment))

    # Recalculate final
    from app.core.config import settings
    tpl_result = await db.execute(select(Job).where(Job.id == score.application.job_id))
    job = tpl_result.scalar_one_or_none()
    if job and job.scoring_template:
        tpl = job.scoring_template
    else:
        tpl = None
        from app.shared.constants.scoring import DEFAULT_WEIGHTS

    # Simple recalc using stored weights
    # (in production, fetch actual template)
    score.final_score = (
        score.skill_match_score * 0.4 +
        score.experience_score * 0.2 +
        score.education_score * 0.1 +
        score.portfolio_score * 0.1 +
        score.soft_skill_score * 0.1 +
        score.administrative_score * 0.1
    )

    score.is_manual_override = True
    score.manual_override_reason = reason
    score.manual_override_by = current_user.id

    # Audit log
    audit = AuditLog(
        company_id=current_user.company_id,
        user_id=current_user.id,
        action="manual_override_score",
        entity_type="candidate_score",
        entity_id=score.id,
        old_values={"final_score": old_final},
        new_values={"final_score": score.final_score, "reason": reason},
    )
    db.add(audit)
    await db.commit()

    return StandardResponse.ok(data={
        "application_id": application_id,
        "new_final_score": round(score.final_score, 2),
        "is_manual_override": True,
    })
