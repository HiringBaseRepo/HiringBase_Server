"""Screening business logic."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.explanation.generator import generate_explanation
from app.ai.matcher.semantic_matcher import match_candidate_to_job
from app.ai.redflag.detector import detect_red_flags
from app.ai.scoring.engine import (
    calculate_final_score,
    get_application_status,
    score_education,
    score_experience,
    score_portfolio,
)
from app.core.exceptions import (
    ApplicationNotFoundException,
    MissingDocumentsException,
    RuleNotFoundException,
)
from app.features.applications.models import ApplicationStatusLog
from app.features.audit_logs.models import AuditLog
from app.features.jobs.models import JobKnockoutRule, JobScoringTemplate
from app.features.screening.models import CandidateScore
from app.features.screening.repositories.repository import (
    add_audit_log,
    add_status_log,
    get_active_knockout_rules,
    get_answers_by_application_id,
    get_application_by_id,
    get_application_for_company,
    get_candidate_score_for_company,
    get_documents_by_application_id,
    get_job_by_id,
    get_knockout_rule_by_id,
    get_requirements_by_job_id,
    get_scoring_template_by_job_id,
    save_candidate_score,
    save_knockout_rule,
)
from app.features.screening.repositories.repository import (
    delete_knockout_rule as delete_knockout_rule_query,
)
from app.features.screening.schemas.schema import (
    KnockoutRuleCreateCommand,
    KnockoutRuleCreatedResponse,
    KnockoutRuleDeletedResponse,
    ManualOverrideResponse,
    ScreeningQueuedResponse,
)
from app.features.screening.services.helpers import evaluate_knockout_rule
from app.features.screening.services.parser import (
    _score_soft_skills,
    build_candidate_profile,
)
from app.features.screening.services.validator_step import run_document_semantic_check
from app.features.users.models import User
from app.shared.constants.scoring import (
    MINIMUM_PASS_SCORE,
    get_default_scoring_template,
)
from app.shared.enums.application_status import ApplicationStatus
from app.shared.enums.document_type import DocumentType


async def create_knockout_rule(
    db: AsyncSession,
    data: KnockoutRuleCreateCommand,
) -> KnockoutRuleCreatedResponse:
    rule = JobKnockoutRule(
        job_id=data.job_id,
        rule_name=data.rule_name,
        rule_type=data.rule_type,
        field_key=data.field_key,
        operator=data.operator,
        target_value=data.target_value,
        action=data.action,
    )
    rule = await save_knockout_rule(db, rule)
    await db.commit()
    return KnockoutRuleCreatedResponse(rule_id=rule.id, job_id=data.job_id)


async def delete_knockout_rule(
    db: AsyncSession, rule_id: int
) -> KnockoutRuleDeletedResponse:
    rule = await get_knockout_rule_by_id(db, rule_id)
    if not rule:
        raise RuleNotFoundException()
    await delete_knockout_rule_query(db, rule)
    await db.commit()
    return KnockoutRuleDeletedResponse(deleted=True)


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
    return ScreeningQueuedResponse(message="Screening queued")


async def process_screening_with_exception_handling(
    application_id: int, company_id: int | None
) -> None:
    """Wrapper for process_screening that handles exceptions in BackgroundTasks."""
    try:
        await process_screening(application_id, company_id)
    except MissingDocumentsException:
        # Exception already handled in process_screening
        pass


async def process_screening(application_id: int, company_id: int | None) -> None:
    from app.core.database.session import get_session

    async with get_session() as db:
        application = await get_application_by_id(db, application_id)
        if not application:
            return
        job = await get_job_by_id(db, application.job_id)
        if not job:
            return

        try:
            application.status = ApplicationStatus.DOC_CHECK
            rules = await get_active_knockout_rules(db, job.id)
            
            # Langkah 1: Validasi kelengkapan dokumen wajib (Dynamic dari Knockout Rules)
            docs = await get_documents_by_application_id(db, application_id)
            doc_types = {doc.document_type for doc in docs}
            required_doc_rules = [r for r in rules if r.rule_type == "document"]
            
            for rule in required_doc_rules:
                # Target value berisi DocumentType enum value (misal: "KTP", "IJAZAH")
                if rule.target_value not in [d.value for d in doc_types]:
                    raise MissingDocumentsException([rule.target_value])
            
            answers = await get_answers_by_application_id(db, application_id)
            for rule in rules:
                if not evaluate_knockout_rule(rule, application, docs, answers=answers):
                    application.status = ApplicationStatus.KNOCKOUT
                    await add_status_log(
                        db,
                        ApplicationStatusLog(
                            application_id=application.id,
                            to_status=ApplicationStatus.KNOCKOUT.value,
                            reason=f"Knockout rule failed: {rule.rule_name}",
                        ),
                    )
                    await db.commit()
                    return

            # Langkah 2 & 3: OCR JIT & Validasi Semantik Dokumen Berbasis LLM
            doc_validation_flags = await run_document_semantic_check(
                docs, application.applicant
            )

            answers = await get_answers_by_application_id(db, application_id)

            # Build parsed_data from form answers
            parsed_data = build_candidate_profile(application, answers)

            # Combine all text answers into one 'text' for soft skill analysis
            text_parts = []
            for ans in answers:
                if ans.value_text:
                    text_parts.append(ans.value_text)
            text = "\n".join(text_parts)

            template = await get_scoring_template_by_job_id(
                db, job.id
            ) or JobScoringTemplate(**get_default_scoring_template())
            requirements = await get_requirements_by_job_id(db, job.id)
            match_result = await match_candidate_to_job(
                parsed_data, requirements, job.description
            )
            exp_score = score_experience(
                parsed_data.get("total_years_experience", 0),
                next(
                    (req.value for req in requirements if req.category == "experience"),
                    "0",
                ),
            )
            edu_score = score_education(
                parsed_data.get("education", []),
                next(
                    (req.value for req in requirements if req.category == "education"),
                    "",
                ),
            )
            portfolio_score = score_portfolio(parsed_data)
            soft_skill_score = _score_soft_skills(text)
            admin_score = 100.0
            final = calculate_final_score(
                skill_match_score=match_result["match_percentage"],
                experience_score=exp_score,
                education_score=edu_score,
                portfolio_score=portfolio_score,
                soft_skill_score=soft_skill_score,
                administrative_score=admin_score,
                skill_match_weight=template.skill_match_weight,
                experience_weight=template.experience_weight,
                education_weight=template.education_weight,
                portfolio_weight=template.portfolio_weight,
                soft_skill_weight=template.soft_skill_weight,
                administrative_weight=template.administrative_weight,
            )

            red_flags = detect_red_flags(parsed_data, text)
            # Tambahkan hasil validasi dokumen ke red flags
            if doc_validation_flags:
                red_flags["red_flags"].extend(doc_validation_flags)
                red_flags["risk_level"] = "high"
            explanation = await generate_explanation(
                match_result,
                exp_score,
                edu_score,
                portfolio_score,
                soft_skill_score,
                admin_score,
                final,
                red_flags,
            )
            await save_candidate_score(
                db,
                CandidateScore(
                    application_id=application.id,
                    skill_match_score=match_result["match_percentage"],
                    experience_score=exp_score,
                    education_score=edu_score,
                    portfolio_score=portfolio_score,
                    soft_skill_score=soft_skill_score,
                    administrative_score=admin_score,
                    final_score=final,
                    explanation=explanation,
                    red_flags=red_flags.get("red_flags"),
                    risk_level=red_flags.get("risk_level"),
                ),
            )
            application.status = get_application_status(final)
            await add_status_log(
                db,
                ApplicationStatusLog(
                    application_id=application.id,
                    to_status=application.status.value,
                    reason=f"AI screening complete. Final score: {final:.1f}",
                ),
            )
            await db.commit()
        except MissingDocumentsException as e:
            application.status = ApplicationStatus.DOC_FAILED
            await add_status_log(
                db,
                ApplicationStatusLog(
                    application_id=application.id,
                    from_status=ApplicationStatus.APPLIED.value,
                    to_status=ApplicationStatus.DOC_FAILED.value,
                    reason=str(e),
                ),
            )
            await db.commit()


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
        raise ApplicationNotFoundException("Candidate score not found")

    old_final = score.final_score
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
    score.is_manual_override = True
    score.manual_override_reason = reason
    score.manual_override_by = current_user.id
    await add_audit_log(
        db,
        AuditLog(
            company_id=current_user.company_id,
            user_id=current_user.id,
            action="manual_override_score",
            entity_type="candidate_score",
            entity_id=score.id,
            old_values={"final_score": old_final},
            new_values={"final_score": score.final_score, "reason": reason},
        ),
    )
    await db.commit()
    return ManualOverrideResponse(
        application_id=application_id,
        new_final_score=round(score.final_score, 2),
        is_manual_override=True,
    )


def _clamp_score(value: float) -> float:
    return max(0, min(100, value))
