"""Screening business logic."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.explanation.generator import generate_explanation
from app.ai.matcher.semantic_matcher import match_candidate_to_job
from app.ai.redflag.detector import detect_red_flags
from app.core.exceptions import (
    ApplicationNotFoundException,
    JobNotFoundException,
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
    _score_education,
    _score_experience,
    _score_portfolio,
    _score_soft_skills,
    build_candidate_profile,
)
from app.features.screening.services.validator_step import run_document_semantic_check
from app.features.users.models import User
from app.shared.constants.scoring import MINIMUM_PASS_SCORE
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


async def process_screening(application_id: int, company_id: int | None) -> None:
    from app.core.database.session import get_session

    async with get_session() as db:
        application = await get_application_by_id(db, application_id)
        if not application:
            return
        job = await get_job_by_id(db, application.job_id)
        if not job:
            return

        docs = await get_documents_by_application_id(db, application_id)
        doc_types = {doc.document_type for doc in docs}
        required_docs = {DocumentType.KTP, DocumentType.IJAZAH}
        missing = required_docs - doc_types
        if missing:
            application.status = ApplicationStatus.DOC_FAILED
            await add_status_log(
                db,
                ApplicationStatusLog(
                    application_id=application.id,
                    from_status=ApplicationStatus.APPLIED.value,
                    to_status=ApplicationStatus.DOC_FAILED.value,
                    reason=f"Missing documents: {[doc.value for doc in missing]}",
                ),
            )
            await db.commit()
            return

        application.status = ApplicationStatus.DOC_CHECK
        rules = await get_active_knockout_rules(db, job.id)
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

        template = (
            await get_scoring_template_by_job_id(db, job.id) or _default_template()
        )
        requirements = await get_requirements_by_job_id(db, job.id)
        match_result = await match_candidate_to_job(
            parsed_data, requirements, job.description
        )
        exp_score = _score_experience(
            parsed_data.get("total_years_experience", 0),
            next(
                (req.value for req in requirements if req.category == "experience"), "0"
            ),
        )
        edu_score = _score_education(
            parsed_data.get("education", []),
            next(
                (req.value for req in requirements if req.category == "education"), ""
            ),
        )
        portfolio_score = _score_portfolio(parsed_data)
        soft_skill_score = _score_soft_skills(text)
        admin_score = 100.0
        final = (
            match_result["match_percentage"] * template.skill_match_weight
            + exp_score * template.experience_weight
            + edu_score * template.education_weight
            + portfolio_score * template.portfolio_weight
            + soft_skill_score * template.soft_skill_weight
            + admin_score * template.administrative_weight
        ) / 100.0

        red_flags = detect_red_flags(parsed_data, text)
        # Tambahkan hasil validasi dokumen ke red flags
        if doc_validation_flags:
            red_flags["red_flags"].extend(doc_validation_flags)
            red_flags["risk_level"] = "high"
        explanation = generate_explanation(
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
        application.status = (
            ApplicationStatus.AI_PASSED
            if final >= MINIMUM_PASS_SCORE
            else ApplicationStatus.UNDER_REVIEW
        )
        await add_status_log(
            db,
            ApplicationStatusLog(
                application_id=application.id,
                to_status=application.status.value,
                reason=f"AI screening complete. Final score: {final:.1f}",
            ),
        )
        await db.commit()


def _default_template() -> JobScoringTemplate:
    return JobScoringTemplate(
        skill_match_weight=40,
        experience_weight=20,
        education_weight=10,
        portfolio_weight=10,
        soft_skill_weight=10,
        administrative_weight=10,
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
    score.final_score = (
        score.skill_match_score * 0.4
        + score.experience_score * 0.2
        + score.education_score * 0.1
        + score.portfolio_score * 0.1
        + score.soft_skill_score * 0.1
        + score.administrative_score * 0.1
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
