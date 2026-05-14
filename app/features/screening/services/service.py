"""Screening business logic."""

import json
import re
import structlog
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
from app.core.utils.audit import get_model_snapshot
from app.features.applications.models import ApplicationStatusLog
from app.features.audit_logs.models import AuditLog
from app.features.audit_logs.repositories.repository import create_audit_log
from app.features.jobs.models import JobKnockoutRule, JobScoringTemplate
from app.features.screening.models import CandidateScore
from app.features.screening.repositories.repository import (
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
    get_candidate_score_by_app_id,
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
from app.features.screening.services.helpers import normalize_knockout_operator
from app.features.screening.services.parser import (
    _score_soft_skills,
    build_candidate_profile,
)
from app.features.screening.services.quota import (
    clear_recovery_retry_count,
    register_manual_screening_request,
)
from app.features.screening.services.validator_step import run_document_semantic_check
from app.features.users.models import User
from app.shared.constants.scoring import (
    get_default_scoring_template,
)
from app.shared.constants.audit_actions import (
    AUTOMATED_SCREENING_CREATE,
    AUTOMATED_SCREENING_FALLBACK,
    AUTOMATED_SCREENING_UPDATE,
    MANUAL_OVERRIDE_SCORE,
)
from app.shared.constants.audit_entities import APPLICATION, CANDIDATE_SCORE
from app.shared.enums.application_status import ApplicationStatus
from app.shared.enums.knockout import KnockoutAction, KnockoutRuleType
from app.shared.enums.risk_level import RiskLevel
from app.shared.helpers.localization import get_label

logger = structlog.get_logger(__name__)

async def create_knockout_rule(
    db: AsyncSession,
    data: KnockoutRuleCreateCommand,
) -> KnockoutRuleCreatedResponse:
    rule = JobKnockoutRule(
        job_id=data.job_id,
        rule_name=data.rule_name,
        rule_type=data.rule_type.value,
        field_key=data.field_key,
        operator=normalize_knockout_operator(data.operator.value),
        target_value=data.target_value,
        action=data.action.value,
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
    decision = await register_manual_screening_request(application_id)
    message_key = (
        decision.reason
        if decision.reason
        else "Proses screening telah dimasukkan dalam antrean"
    )
    return ScreeningQueuedResponse(
        message=get_label(message_key),
        queue_status=decision.queue_status,
        task_enqueued=decision.task_enqueued,
    )


async def process_screening_with_exception_handling(
    application_id: int,
    company_id: int | None,
    *,
    trigger_source: str,
    force_fallback: bool = False,
) -> bool:
    """Wrapper for process_screening that handles exceptions in BackgroundTasks."""
    try:
        await process_screening(
            application_id,
            company_id,
            trigger_source=trigger_source,
            force_fallback=force_fallback,
        )
        return True
    except MissingDocumentsException:
        # Exception already handled in process_screening
        return True
    except Exception as exc:
        logger.exception(
            "screening_processing_failed",
            application_id=application_id,
            company_id=company_id,
            trigger_source=trigger_source,
            error=str(exc),
        )
        await handle_screening_failure(
            application_id=application_id,
            company_id=company_id,
            trigger_source=trigger_source,
            reason=str(exc),
        )
        return False


async def process_screening(
    application_id: int,
    company_id: int | None,
    *,
    trigger_source: str,
    force_fallback: bool = False,
) -> None:
    from app.core.database.session import get_session

    async with get_session() as db:
        application = await get_application_by_id(db, application_id)
        if not application:
            return
        job = await get_job_by_id(db, application.job_id)
        if not job:
            return

        try:
            previous_status = application.status
            application.status = ApplicationStatus.DOC_CHECK
            await add_status_log(
                db,
                ApplicationStatusLog(
                    application_id=application.id,
                    from_status=previous_status.value if previous_status else None,
                    to_status=ApplicationStatus.DOC_CHECK.value,
                    reason="Screening dimulai: verifikasi dokumen",
                    metadata_snapshot={"trigger_source": trigger_source},
                ),
            )
            await db.commit()
            rules = await get_active_knockout_rules(db, job.id)
            
            # Step 1: Validate mandatory document completeness (Dynamic from Knockout Rules)
            docs = await get_documents_by_application_id(db, application_id)
            doc_types = {doc.document_type for doc in docs}
            required_doc_rules = [r for r in rules if r.rule_type == KnockoutRuleType.DOCUMENT.value]
            
            for rule in required_doc_rules:
                # Target value contains DocumentType enum value (e.g., "identity_card", "degree")
                if rule.target_value not in [d.value for d in doc_types]:
                    raise MissingDocumentsException([rule.target_value])
            
            answers = await get_answers_by_application_id(db, application_id)
            
            # Fallback to application.notes if no answers in table
            if not answers and application.notes:
                try:
                    json.loads(application.notes)
                    logger.debug(
                        "screening_notes_fallback_available",
                        application_id=application_id,
                    )
                except (json.JSONDecodeError, TypeError):
                    logger.warning(
                        "screening_notes_fallback_invalid_json",
                        application_id=application_id,
                    )

            logger.debug(
                "screening_inputs_loaded",
                application_id=application_id,
                answers_count=len(answers),
                docs_count=len(docs),
            )

            for rule in rules:
                if not evaluate_knockout_rule(rule, application, docs, answers=answers):
                    target_status = (
                        ApplicationStatus.UNDER_REVIEW
                        if rule.action == KnockoutAction.PENDING_REVIEW.value
                        else ApplicationStatus.KNOCKOUT
                    )
                    application.status = target_status
                    await add_status_log(
                        db,
                        ApplicationStatusLog(
                            application_id=application.id,
                            from_status=ApplicationStatus.DOC_CHECK.value,
                            to_status=target_status.value,
                            reason=f"Gagal kualifikasi (Knockout): {rule.rule_name}",
                            metadata_snapshot={"trigger_source": trigger_source},
                        ),
                    )
                    await db.commit()
                    await clear_recovery_retry_count(application.id)
                    return

            application.status = ApplicationStatus.AI_PROCESSING
            await add_status_log(
                db,
                ApplicationStatusLog(
                    application_id=application.id,
                    from_status=ApplicationStatus.DOC_CHECK.value,
                    to_status=ApplicationStatus.AI_PROCESSING.value,
                    reason="Dokumen valid, lanjut proses AI",
                    metadata_snapshot={"trigger_source": trigger_source},
                ),
            )
            await db.commit()

            # Langkah 2 & 3: OCR JIT & Validasi Semantik Dokumen Berbasis LLM
            doc_validation_flags, ocr_results = await run_document_semantic_check(
                docs, application.applicant, force_fallback=force_fallback
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
                parsed_data, requirements, job.description, force_fallback=force_fallback
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
            soft_skill_score = await _score_soft_skills(text, force_fallback=force_fallback)
            admin_score = 100.0
            # Step 2: Document check flags
            if doc_validation_flags:
                # If high risk document flags exist, set admin score to 0
                if any(f.get("risk_level") == RiskLevel.HIGH.value for f in doc_validation_flags if isinstance(f, dict)):
                    admin_score = 0.0

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

            # Merge all red flags using helper
            red_flags = await _merge_red_flags(parsed_data, text, ocr_results, doc_validation_flags, force_fallback=force_fallback)
            
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
            
            # Clean up AI thought tags
            explanation = re.sub(r"<think>.*?</think>", "", explanation, flags=re.DOTALL).strip()

            # UPSERT LOGIC
            existing_score = await get_candidate_score_by_app_id(db, application.id)
            if existing_score:
                # Capture snapshot for Audit Log
                old_values = get_model_snapshot(existing_score)
                
                # Update existing
                existing_score.skill_match_score = match_result["match_percentage"]
                existing_score.experience_score = exp_score
                existing_score.education_score = edu_score
                existing_score.portfolio_score = portfolio_score
                existing_score.soft_skill_score = soft_skill_score
                existing_score.administrative_score = admin_score
                existing_score.final_score = final
                existing_score.explanation = explanation
                existing_score.red_flags = red_flags["red_flags"]
                existing_score.risk_level = red_flags["risk_level"]
                
                # Create Audit Log for automated update
                await create_audit_log(
                    db,
                    AuditLog(
                        company_id=company_id,
                        user_id=None,  # System automated
                        action=AUTOMATED_SCREENING_UPDATE,
                        entity_type=CANDIDATE_SCORE,
                        entity_id=existing_score.id,
                        old_values=old_values,
                        new_values={
                            "final_score": final,
                            "risk_level": red_flags["risk_level"],
                            "trigger_source": trigger_source,
                        },
                    )
                )
            else:
                # Create new
                score = await save_candidate_score(
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
                        red_flags=red_flags["red_flags"],
                        risk_level=red_flags["risk_level"],
                    ),
                )
                await create_audit_log(
                    db,
                    AuditLog(
                        company_id=company_id,
                        user_id=None,
                        action=AUTOMATED_SCREENING_CREATE,
                        entity_type=CANDIDATE_SCORE,
                        entity_id=score.id,
                        new_values={
                            "final_score": final,
                            "risk_level": red_flags["risk_level"],
                            "trigger_source": trigger_source,
                        },
                    ),
                )
            # Final status mapping
            if red_flags.get("risk_level") == RiskLevel.HIGH.value:
                application.status = ApplicationStatus.REJECTED
            else:
                calculated_status = get_application_status(final)
                if calculated_status == ApplicationStatus.APPLIED:
                    calculated_status = ApplicationStatus.UNDER_REVIEW
                application.status = calculated_status
            await add_status_log(
                db,
                ApplicationStatusLog(
                    application_id=application.id,
                    from_status=ApplicationStatus.AI_PROCESSING.value,
                    to_status=application.status.value,
                    reason=get_label("screening_completed_reason", score=f"{final:.1f}"),
                    metadata_snapshot={"trigger_source": trigger_source},
                ),
            )
            await db.commit()
            await clear_recovery_retry_count(application.id)
        except MissingDocumentsException as e:
            application.status = ApplicationStatus.DOC_FAILED
            await add_status_log(
                db,
                ApplicationStatusLog(
                    application_id=application.id,
                    from_status=ApplicationStatus.DOC_CHECK.value,
                    to_status=ApplicationStatus.DOC_FAILED.value,
                    reason=str(e),
                    metadata_snapshot={"trigger_source": trigger_source},
                ),
            )
            await db.commit()
            await clear_recovery_retry_count(application.id)


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
        raise ApplicationNotFoundException("Skor kandidat tidak ditemukan")

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


async def handle_screening_failure(
    *,
    application_id: int,
    company_id: int | None,
    trigger_source: str,
    reason: str,
) -> None:
    """Move failed automatic screenings to safe manual review state."""
    from app.core.database.session import get_session

    async with get_session() as db:
        application = await get_application_by_id(db, application_id)
        if not application:
            return

        if application.status not in {
            ApplicationStatus.APPLIED,
            ApplicationStatus.DOC_CHECK,
            ApplicationStatus.AI_PROCESSING,
        }:
            return

        old_values = get_model_snapshot(application)
        previous_status = application.status
        application.status = ApplicationStatus.UNDER_REVIEW

        await add_status_log(
            db,
            ApplicationStatusLog(
                application_id=application.id,
                from_status=previous_status.value if previous_status else None,
                to_status=ApplicationStatus.UNDER_REVIEW.value,
                reason=get_label("screening_fallback_under_review"),
                metadata_snapshot={
                    "trigger_source": trigger_source,
                    "failure_reason": reason,
                },
            ),
        )
        await create_audit_log(
            db,
            AuditLog(
                company_id=company_id,
                user_id=None,
                action=AUTOMATED_SCREENING_FALLBACK,
                entity_type=APPLICATION,
                entity_id=application.id,
                old_values=old_values,
                new_values={
                    "status": ApplicationStatus.UNDER_REVIEW.value,
                    "reason": reason,
                    "trigger_source": trigger_source,
                },
            ),
        )
        await clear_recovery_retry_count(application.id)


def _clamp_score(value: float) -> float:
    return max(0, min(100, value))


async def _merge_red_flags(
    parsed_data: dict, 
    text: str, 
    ocr_results: dict, 
    doc_validation_flags: list[dict],
    force_fallback: bool = False
) -> dict:
    """Helper to merge all red flags from different sources."""
    # Base red flags from detector
    red_flags = await detect_red_flags(
        parsed_data, text, doc_ocr_results=ocr_results, force_fallback=force_fallback
    )
    
    # Merge document validation flags
    if doc_validation_flags:
        for flag in doc_validation_flags:
            if isinstance(flag, dict):
                red_flags["red_flags"].append(flag)
            else:
                # Fallback for legacy string flags
                red_flags["red_flags"].append({
                    "message": str(flag),
                    "risk_level": RiskLevel.HIGH.value,
                    "type": "document"
                })
        
        # If any doc flag is high, ensure overall risk is high
        if any(f.get("risk_level") == RiskLevel.HIGH.value for f in doc_validation_flags if isinstance(f, dict)):
            red_flags["risk_level"] = RiskLevel.HIGH.value
            
    return red_flags
