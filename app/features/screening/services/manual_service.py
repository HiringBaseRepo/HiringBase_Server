"""Manual screening actions service."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ApplicationNotFoundException
from app.core.utils.audit import get_model_snapshot
from app.features.audit_logs.models import AuditLog
from app.features.audit_logs.repositories.repository import create_audit_log
from app.features.jobs.models import JobScoringTemplate
from app.features.screening.repositories.repository import (
    get_application_for_company,
    get_candidate_score_for_company,
    get_application_by_id,
    get_scoring_template_by_job_id,
)
from app.features.screening.schemas.schema import (
    ManualOverrideResponse,
    ScreeningQueuedResponse,
)
from app.features.screening.services.quota import (
    register_manual_screening_request,
)
from app.features.users.models import User
from app.shared.constants.scoring import get_default_scoring_template
from app.shared.constants.audit_actions import MANUAL_OVERRIDE_SCORE
from app.shared.constants.audit_entities import CANDIDATE_SCORE
from app.shared.constants.errors import (
    ERR_CANDIDATE_SCORE_NOT_FOUND,
    MSG_SCREENING_QUEUED,
)
from app.shared.helpers.localization import get_label

def _clamp_score(value: float) -> float:
    return max(0, min(100, value))


async def queue_screening(
    db: AsyncSession,
    *,
    current_user: User,
    application_id: int,
) -> ScreeningQueuedResponse:
    application = await get_application_for_company(
        db,
        application_id=application_id,
        company_id=current_user.company_id,
    )
    if not application:
        raise ApplicationNotFoundException()
    decision = await register_manual_screening_request(application_id)
    message_key = (
        decision.reason
        if decision.reason
        else MSG_SCREENING_QUEUED
    )
    return ScreeningQueuedResponse(
        message=get_label(message_key),
        queue_status=decision.queue_status,
        task_enqueued=decision.task_enqueued,
    )


async def manual_override_score(
    db: AsyncSession,
    *,
    current_user: User,
    application_id: int,
    skill_adjustment: float = 0.0,
    experience_adjustment: float = 0.0,
    education_adjustment: float = 0.0,
    portfolio_adjustment: float = 0.0,
    soft_skill_adjustment: float = 0.0,
    admin_adjustment: float = 0.0,
    reason: str = "",
) -> ManualOverrideResponse:
    score = await get_candidate_score_for_company(
        db,
        application_id=application_id,
        company_id=current_user.company_id,
    )
    if not score:
        raise ApplicationNotFoundException(get_label(ERR_CANDIDATE_SCORE_NOT_FOUND))

    old_values = get_model_snapshot(score)
    score.skill_match_score = _clamp_score(score.skill_match_score + skill_adjustment)
    score.experience_score = _clamp_score(
        score.experience_score + experience_adjustment
    )
    score.education_score = _clamp_score(score.education_score + education_adjustment)
    score.portfolio_score = _clamp_score(score.portfolio_score + portfolio_adjustment)
    score.soft_skill_score = _clamp_score(
        score.soft_skill_score + soft_skill_adjustment
    )
    score.administrative_score = _clamp_score(
        score.administrative_score + admin_adjustment
    )

    # Ambil template bobot dari Job
    application = await get_application_by_id(db, application_id)
    template = await get_scoring_template_by_job_id(
        db, application.job_id
    ) or JobScoringTemplate(**get_default_scoring_template())

    score.final_score = (
        (score.skill_match_score * template.skill_match_weight / 100.0)
        + (score.experience_score * template.experience_weight / 100.0)
        + (score.education_score * template.education_weight / 100.0)
        + (score.portfolio_score * template.portfolio_weight / 100.0)
        + (score.soft_skill_score * template.soft_skill_weight / 100.0)
        + (score.administrative_score * template.administrative_weight / 100.0)
    )
    if isinstance(score.scoring_breakdown, dict):
        score.scoring_breakdown["final_score"] = round(score.final_score, 2)
        score.scoring_breakdown["manual_override"] = {
            "applied": True,
            "reason": reason,
            "by_user_id": current_user.id,
        }
    score.is_manual_override = True
    score.manual_override_reason = reason
    score.manual_override_by = current_user.id
    await create_audit_log(
        db,
        AuditLog(
            company_id=current_user.company_id,
            user_id=current_user.id,
            action=MANUAL_OVERRIDE_SCORE,
            entity_type=CANDIDATE_SCORE,
            entity_id=score.id,
            old_values=old_values,
            new_values={"final_score": score.final_score, "reason": reason},
        ),
    )
    await db.commit()
    return ManualOverrideResponse(
        application_id=application_id,
        new_final_score=round(score.final_score, 2),
        is_manual_override=True,
    )
