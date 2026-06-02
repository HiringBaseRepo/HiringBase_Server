"""Screening orchestrator."""

import json
import re
from typing import Any
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.explanation.generator import generate_explanation
from app.ai.matcher.semantic_matcher import match_candidate_to_job
from app.ai.scoring.engine import (
    build_scoring_breakdown,
    calculate_final_score,
    get_application_status,
)
from app.core.exceptions import (
    MissingDocumentsException,
)
from app.core.utils.audit import get_model_snapshot
from app.features.applications.models import ApplicationStatusLog
from app.features.audit_logs.models import AuditLog
from app.features.audit_logs.repositories.repository import create_audit_log
from app.features.jobs.models import JobScoringTemplate
from app.features.notifications.services.service import create_notification_for_internal_audience
from app.features.screening.models import CandidateScore
from app.features.screening.repositories.repository import (
    add_status_log,
    get_active_knockout_rules,
    get_answers_by_application_id,
    get_application_by_id,
    get_candidate_score_by_app_id,
    get_documents_by_application_id,
    get_job_by_id,
    get_requirements_by_job_id,
    get_scoring_template_by_job_id,
    save_candidate_score,
)
from app.features.screening.services.helpers import (
    evaluate_knockout_rule,
    merge_red_flags,
    build_scoring_gate_flags,
    get_document_type_label,
)
from app.features.screening.services.parser import (
    _score_soft_skills,
    build_candidate_profile,
)
from app.features.screening.services.quota import (
    clear_recovery_retry_count,
)
from app.features.screening.services.validator_step import run_document_semantic_check
from app.shared.constants.scoring import (
    get_default_scoring_template,
)
from app.shared.constants.audit_actions import (
    AUTOMATED_SCREENING_CREATE,
    AUTOMATED_SCREENING_FALLBACK,
    AUTOMATED_SCREENING_UPDATE,
)
from app.shared.constants.audit_entities import APPLICATION, CANDIDATE_SCORE
from app.shared.enums.application_status import ApplicationStatus
from app.shared.enums.knockout import KnockoutAction, KnockoutRuleType
from app.shared.enums.notification_type import NotificationType
from app.shared.enums.risk_level import RiskLevel
from app.shared.helpers.localization import get_label

logger = structlog.get_logger(__name__)


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
            # 1. Dokumen check & Knockout Rules Evaluation
            passed_knockout, docs, answers = await _run_doc_check_phase(
                db, application, job, trigger_source, company_id
            )
            if not passed_knockout:
                return

            # 2. AI Scoring, LLM matching, & Candidate Score Upsert
            await _run_ai_scoring_phase(
                db, application, job, docs, answers, trigger_source, company_id, force_fallback
            )

        except MissingDocumentsException:
            application.status = ApplicationStatus.DOC_FAILED
            await add_status_log(
                db,
                ApplicationStatusLog(
                    application_id=application.id,
                    from_status=ApplicationStatus.DOC_CHECK.value,
                    to_status=ApplicationStatus.DOC_FAILED.value,
                    reason=get_label("screening_missing_documents_reason"),
                    metadata_snapshot={"trigger_source": trigger_source},
                ),
            )
            await create_notification_for_internal_audience(
                db,
                actor_user_id=None,
                company_id=company_id,
                notification_type=NotificationType.DOCUMENT_FAILED,
                entity_type=APPLICATION,
                entity_id=application.id,
                message_params={
                    "applicant_name": application.applicant.full_name if application.applicant else "-",
                    "job_title": job.title if job else "-",
                },
            )
            await db.commit()
            await clear_recovery_retry_count(application.id)


async def _run_doc_check_phase(
    db: AsyncSession,
    application: Any,
    job: Any,
    trigger_source: str,
    company_id: int | None,
) -> tuple[bool, list, list]:
    """Execute Document Check and Evaluate Knockout Rules."""
    previous_status = application.status
    application.status = ApplicationStatus.DOC_CHECK
    await add_status_log(
        db,
        ApplicationStatusLog(
            application_id=application.id,
            from_status=previous_status.value if previous_status else None,
            to_status=ApplicationStatus.DOC_CHECK.value,
            reason=get_label("screening_doc_check_started"),
            metadata_snapshot={"trigger_source": trigger_source},
        ),
    )
    await db.commit()

    rules = await get_active_knockout_rules(db, job.id)
    
    # Validate mandatory document completeness
    docs = await get_documents_by_application_id(db, application.id)
    doc_types = {doc.document_type for doc in docs}
    required_doc_rules = [r for r in rules if r.rule_type == KnockoutRuleType.DOCUMENT.value]
    
    for rule in required_doc_rules:
        if rule.target_value not in [d.value for d in doc_types]:
            raise MissingDocumentsException([rule.target_value])
    
    answers = await get_answers_by_application_id(db, application.id)
    
    # Fallback to application.notes if no answers in table
    if not answers and application.notes:
        try:
            json.loads(application.notes)
            logger.debug(
                "screening_notes_fallback_available",
                application_id=application.id,
            )
        except (json.JSONDecodeError, TypeError):
            logger.warning(
                "screening_notes_fallback_invalid_json",
                application_id=application.id,
            )

    logger.debug(
        "screening_inputs_loaded",
        application_id=application.id,
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
                    reason=get_label(
                        "screening_knockout_failed_reason",
                        rule_name=rule.rule_name,
                    ),
                    metadata_snapshot={"trigger_source": trigger_source},
                ),
            )
            knockout_notification_type = (
                NotificationType.SCREENING_UNDER_REVIEW
                if target_status == ApplicationStatus.UNDER_REVIEW
                else NotificationType.SCREENING_REJECTED
            )
            await create_notification_for_internal_audience(
                db,
                actor_user_id=None,
                company_id=company_id,
                notification_type=knockout_notification_type,
                entity_type=APPLICATION,
                entity_id=application.id,
                message_params={
                    "applicant_name": application.applicant.full_name if application.applicant else "-",
                    "job_title": job.title if job else "-",
                },
            )
            await db.commit()
            await clear_recovery_retry_count(application.id)
            return False, docs, answers

    return True, docs, answers


async def _run_ai_scoring_phase(
    db: AsyncSession,
    application: Any,
    job: Any,
    docs: list,
    answers: list,
    trigger_source: str,
    company_id: int | None,
    force_fallback: bool,
) -> None:
    """Execute OCR, AI Scoring, Explanation Generation, and Score Update."""
    application.status = ApplicationStatus.AI_PROCESSING
    await add_status_log(
        db,
        ApplicationStatusLog(
            application_id=application.id,
            from_status=ApplicationStatus.DOC_CHECK.value,
            to_status=ApplicationStatus.AI_PROCESSING.value,
            reason=get_label("screening_ai_processing_started"),
            metadata_snapshot={"trigger_source": trigger_source},
        ),
    )
    await db.commit()

    # OCR JIT & Validasi Semantik Dokumen Berbasis LLM
    doc_validation_flags, ocr_results, administrative_hard_fail = await run_document_semantic_check(
        docs, application.applicant, force_fallback=force_fallback
    )

    # Re-fetch answers to catch any modifications
    answers = await get_answers_by_application_id(db, application.id)

    # Build parsed_data from form answers
    parsed_data = build_candidate_profile(application, answers)
    text = parsed_data.get("text_blob", "")

    template = await get_scoring_template_by_job_id(
        db, job.id
    ) or JobScoringTemplate(**get_default_scoring_template())
    requirements = await get_requirements_by_job_id(db, job.id)
    
    match_result = await match_candidate_to_job(
        parsed_data, requirements, job.description, force_fallback=force_fallback
    )
    soft_skill_payload = await _score_soft_skills(
        text, force_fallback=force_fallback
    )
    scoring_breakdown = build_scoring_breakdown(
        match_result=match_result,
        parsed_data=parsed_data,
        requirements=requirements,
        soft_skill_payload=soft_skill_payload,
        text=text,
        document_count=len(docs),
        doc_validation_flags=doc_validation_flags,
    )
    
    exp_score = scoring_breakdown["components"]["experience"]["score"]
    edu_score = scoring_breakdown["components"]["education"]["score"]
    portfolio_score = scoring_breakdown["components"]["portfolio"]["score"]
    soft_skill_score = scoring_breakdown["components"]["soft_skill"]["score"]
    admin_score = scoring_breakdown["components"]["administrative"]["score"]
    skill_match_score = scoring_breakdown["components"]["skill_match"]["score"]

    if administrative_hard_fail:
        admin_score = 0.0
        scoring_breakdown["components"]["administrative"]["score"] = 0.0
        scoring_breakdown["components"]["administrative"]["raw_score"] = 0.0
        scoring_breakdown["components"]["administrative"]["rating"] = 1
        scoring_breakdown["components"]["administrative"]["rubric"] = get_label(
            "screening_administrative_hard_fail_rubric"
        )
        scoring_breakdown["components"]["administrative"]["evidence"]["hard_fail"] = {
            "active": True,
            "reason": get_label(
                "screening_document_name_mismatch_flag",
                document_type=get_document_type_label(
                    administrative_hard_fail["document_type"]
                ),
            ),
            "document_type": administrative_hard_fail["document_type"],
            "validator_reason": administrative_hard_fail["reason"],
        }

    final = calculate_final_score(
        skill_match_score=skill_match_score,
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
    red_flags = await merge_red_flags(
        parsed_data,
        text,
        ocr_results,
        doc_validation_flags,
        force_fallback=force_fallback,
        extra_flags=build_scoring_gate_flags(
            scoring_breakdown,
            administrative_hard_fail=administrative_hard_fail,
        ),
    )
    scoring_breakdown["final_score"] = round(final, 2)
    scoring_breakdown["risk_level"] = red_flags["risk_level"]
    if administrative_hard_fail:
        scoring_breakdown["gates"]["administrative_hard_fail"] = True
    
    explanation = await generate_explanation(
        match_result,
        exp_score,
        edu_score,
        portfolio_score,
        soft_skill_score,
        admin_score,
        final,
        red_flags,
        scoring_breakdown,
    )
    
    # Clean up AI thought tags
    explanation = re.sub(r"<think>.*?</think>", "", explanation, flags=re.DOTALL).strip()

    # UPSERT LOGIC
    existing_score = await get_candidate_score_by_app_id(db, application.id)
    if existing_score:
        old_values = get_model_snapshot(existing_score)
        
        existing_score.skill_match_score = skill_match_score
        existing_score.experience_score = exp_score
        existing_score.education_score = edu_score
        existing_score.portfolio_score = portfolio_score
        existing_score.soft_skill_score = soft_skill_score
        existing_score.administrative_score = admin_score
        existing_score.final_score = final
        existing_score.explanation = explanation
        existing_score.red_flags = red_flags["red_flags"]
        existing_score.risk_level = red_flags["risk_level"]
        existing_score.scoring_breakdown = scoring_breakdown
        
        await create_audit_log(
            db,
            AuditLog(
                company_id=company_id,
                user_id=None,
                action=AUTOMATED_SCREENING_UPDATE,
                entity_type=CANDIDATE_SCORE,
                entity_id=existing_score.id,
                old_values=old_values,
                new_values={
                    "final_score": final,
                    "risk_level": red_flags["risk_level"],
                    "gates": scoring_breakdown["gates"]["reasons"],
                    "trigger_source": trigger_source,
                },
            )
        )
    else:
        score = await save_candidate_score(
            db,
            CandidateScore(
                application_id=application.id,
                skill_match_score=skill_match_score,
                experience_score=exp_score,
                education_score=edu_score,
                portfolio_score=portfolio_score,
                soft_skill_score=soft_skill_score,
                administrative_score=admin_score,
                final_score=final,
                explanation=explanation,
                red_flags=red_flags["red_flags"],
                risk_level=red_flags["risk_level"],
                scoring_breakdown=scoring_breakdown,
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
                    "gates": scoring_breakdown["gates"]["reasons"],
                    "trigger_source": trigger_source,
                },
            ),
        )

    # Final status mapping
    if administrative_hard_fail:
        application.status = ApplicationStatus.REJECTED
    elif red_flags.get("risk_level") == RiskLevel.HIGH.value:
        application.status = ApplicationStatus.REJECTED
    elif scoring_breakdown["gates"]["force_under_review"]:
        application.status = ApplicationStatus.UNDER_REVIEW
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

    status_notification_type = None
    if application.status == ApplicationStatus.AI_PASSED:
        status_notification_type = NotificationType.SCREENING_PASSED
    elif application.status == ApplicationStatus.UNDER_REVIEW:
        status_notification_type = NotificationType.SCREENING_UNDER_REVIEW
    elif application.status == ApplicationStatus.REJECTED:
        status_notification_type = NotificationType.SCREENING_REJECTED
    
    if status_notification_type:
        await create_notification_for_internal_audience(
            db,
            actor_user_id=None,
            company_id=company_id,
            notification_type=status_notification_type,
            entity_type=APPLICATION,
            entity_id=application.id,
            message_params={
                "applicant_name": application.applicant.full_name if application.applicant else "-",
                "job_title": job.title if job else "-",
            },
        )
    await db.commit()
    await clear_recovery_retry_count(application.id)


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
