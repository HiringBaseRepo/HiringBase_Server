"""Knockout + Administrative Screening + AI Scoring Engine."""
from typing import Optional, List, Dict
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.core.database.base import get_db
from app.features.auth.dependencies import require_hr, get_current_user
from app.features.models import (
    Job, Application, JobKnockoutRule, ApplicationDocument, CandidateScore,
    ApplicationStatusLog, JobScoringTemplate, JobRequirement, JobFormField,
    ApplicationAnswer, Company
)
from app.shared.schemas.response import StandardResponse
from app.shared.enums.application_status import ApplicationStatus
from app.shared.enums.document_type import DocumentType
from app.shared.constants.errors import ERR_KNOCKOUT_FAIL, ERR_SCORING_TEMPLATE_MISSING
from app.shared.constants.scoring import DEFAULT_WEIGHTS, MINIMUM_PASS_SCORE, EDUCATION_RANK
from app.ai.ocr.engine import extract_text_from_document
from app.ai.parser.resume_parser import parse_resume_text
from app.ai.matcher.semantic_matcher import match_candidate_to_job
from app.ai.explanation.generator import generate_explanation
from app.ai.redflag.detector import detect_red_flags

router = APIRouter(prefix="/screening", tags=["Screening Engine"])


@router.post("/{job_id}/knockout-rules", response_model=StandardResponse[dict])
async def create_knockout_rule(
    job_id: int,
    rule_name: str,
    rule_type: str,
    operator: str,
    target_value: str,
    field_key: Optional[str] = None,
    action: str = "auto_reject",
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_hr),
):
    rule = JobKnockoutRule(
        job_id=job_id,
        rule_name=rule_name,
        rule_type=rule_type,
        field_key=field_key,
        operator=operator,
        target_value=target_value,
        action=action,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return StandardResponse.ok(data={"rule_id": rule.id, "job_id": job_id})


@router.delete("/knockout-rules/{rule_id}", response_model=StandardResponse[dict])
async def delete_knockout_rule(rule_id: int, db: AsyncSession = Depends(get_db), current_user=Depends(require_hr)):
    result = await db.execute(select(JobKnockoutRule).where(JobKnockoutRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        return StandardResponse.error(message="Rule not found", status_code=404)
    await db.delete(rule)
    await db.commit()
    return StandardResponse.ok(data={"deleted": True})


@router.post("/applications/{application_id}/run", response_model=StandardResponse[dict])
async def run_screening(
    application_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_hr),
):
    result = await db.execute(select(Application).join(Job).where(
        Application.id == application_id,
        Job.company_id == current_user.company_id,
    ))
    application = result.scalar_one_or_none()
    if not application:
        return StandardResponse.error(message="Application not found", status_code=404)

    background_tasks.add_task(_process_screening, application_id, current_user.company_id)
    return StandardResponse.ok(data={"message": "Screening queued"}, message="Screening started in background")


async def _process_screening(application_id: int, company_id: int):
    from app.core.database.session import get_session
    async with get_session() as db:
        result = await db.execute(select(Application).where(Application.id == application_id))
        application = result.scalar_one_or_none()
        if not application:
            return

        job_result = await db.execute(select(Job).where(Job.id == application.job_id))
        job = job_result.scalar_one_or_none()
        if not job:
            return

        # 1. Administrative screening
        docs_result = await db.execute(select(ApplicationDocument).where(ApplicationDocument.application_id == application_id))
        docs = docs_result.scalars().all()
        doc_types = {d.document_type for d in docs}
        required_docs = {DocumentType.CV, DocumentType.KTP, DocumentType.IJAZAH}
        missing = required_docs - doc_types

        if missing:
            application.status = ApplicationStatus.DOC_FAILED
            log = ApplicationStatusLog(
                application_id=application.id,
                from_status=ApplicationStatus.APPLIED.value,
                to_status=ApplicationStatus.DOC_FAILED.value,
                reason=f"Missing documents: {[d.value for d in missing]}",
            )
            db.add(log)
            await db.commit()
            return

        application.status = ApplicationStatus.DOC_CHECK

        # 2. Knockout rules — load answers untuk evaluasi experience/boolean/range
        rules_result = await db.execute(select(JobKnockoutRule).where(JobKnockoutRule.job_id == job.id, JobKnockoutRule.is_active == True))
        rules = rules_result.scalars().all()

        answers_result = await db.execute(
            select(ApplicationAnswer).where(ApplicationAnswer.application_id == application_id)
        )
        answers = answers_result.scalars().all()

        for rule in rules:
            passed = _evaluate_knockout_rule(rule, application, docs, answers=answers)
            if not passed:
                application.status = ApplicationStatus.KNOCKOUT
                log = ApplicationStatusLog(
                    application_id=application.id,
                    to_status=ApplicationStatus.KNOCKOUT.value,
                    reason=f"Knockout rule failed: {rule.rule_name}",
                )
                db.add(log)
                await db.commit()
                return

        # 3. CV Parsing
        cv_doc = next((d for d in docs if d.document_type == DocumentType.CV), None)
        parsed_data = {}
        if cv_doc:
            try:
                text = await extract_text_from_document(cv_doc.file_url)
                parsed_data = parse_resume_text(text)
                cv_doc.ocr_text = text
            except Exception:
                pass

        # 4. AI Matching & Scoring
        tpl_result = await db.execute(select(JobScoringTemplate).where(JobScoringTemplate.job_id == job.id))
        tpl = tpl_result.scalar_one_or_none()
        if not tpl:
            tpl = _default_template()

        reqs_result = await db.execute(select(JobRequirement).where(JobRequirement.job_id == job.id))
        reqs = reqs_result.scalars().all()

        match_result = await match_candidate_to_job(parsed_data, reqs, job.description)

        # 5. Experience scoring
        exp_years = parsed_data.get("total_years_experience", 0)
        req_exp = next((r for r in reqs if r.category == "experience"), None)
        exp_score = _score_experience(exp_years, req_exp.value if req_exp else "0")

        # 6. Education scoring
        edu = parsed_data.get("education", [])
        req_edu = next((r for r in reqs if r.category == "education"), None)
        edu_score = _score_education(edu, req_edu.value if req_edu else "")

        # 7. Portfolio scoring
        portfolio_score = _score_portfolio(parsed_data)

        # 8. Soft skill (stub NLP)
        soft_skill_score = 60.0  # MVP default

        # 9. Admin score
        admin_score = 100.0 if not missing else 0.0

        # 10. Final weighted score
        final = (
            match_result["match_percentage"] * tpl.skill_match_weight +
            exp_score * tpl.experience_weight +
            edu_score * tpl.education_weight +
            portfolio_score * tpl.portfolio_weight +
            soft_skill_score * tpl.soft_skill_weight +
            admin_score * tpl.administrative_weight
        ) / 100.0

        # 11. Red flags
        red_flags = detect_red_flags(parsed_data, text if cv_doc else "")

        # 12. Explanation
        explanation = generate_explanation(
            match_result, exp_score, edu_score, portfolio_score, soft_skill_score, admin_score, final
        )

        score = CandidateScore(
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
        )
        db.add(score)

        application.status = ApplicationStatus.AI_PASSED if final >= MINIMUM_PASS_SCORE else ApplicationStatus.UNDER_REVIEW
        log = ApplicationStatusLog(
            application_id=application.id,
            to_status=application.status.value,
            reason=f"AI screening complete. Final score: {final:.1f}",
        )
        db.add(log)
        await db.commit()


def _default_template():
    from app.features.models import JobScoringTemplate
    return JobScoringTemplate(
        skill_match_weight=40, experience_weight=20, education_weight=10,
        portfolio_weight=10, soft_skill_weight=10, administrative_weight=10,
    )


def _evaluate_knockout_rule(rule: JobKnockoutRule, application, docs: list, answers: list = None) -> bool:
    """Evaluasi knockout rule secara deterministik.

    Returns:
        True  → rule LULUS (kandidat boleh lanjut)
        False → rule GAGAL (knockout action berlaku)

    Rule types:
    - document  : cek ketersediaan dokumen wajib
    - experience: cek pengalaman kerja vs threshold
    - education : cek level pendidikan vs threshold
    - boolean   : cek jawaban form (yes/no)
    - range     : cek nilai numerik dalam rentang
    """
    if answers is None:
        answers = []

    rule_type = (rule.rule_type or "").lower()
    operator = (rule.operator or "eq").lower()
    target = rule.target_value

    # --- Document type ---
    if rule_type == "document":
        doc_types = {d.document_type.value for d in docs}
        return target in doc_types

    # --- Experience type ---
    # field_key diisi dengan "total_years_experience" atau key lain
    if rule_type == "experience":
        # Cek dari answers form jika ada
        answer_val = _find_answer_value(rule.field_key, answers)
        if answer_val is not None:
            try:
                years = float(answer_val)
                req = float(target)
                return _compare_numeric(years, req, operator)
            except (ValueError, TypeError):
                pass
        return True  # jika tidak ada data, beri benefit of the doubt

    # --- Education type ---
    if rule_type == "education":
        from app.shared.constants.scoring import EDUCATION_RANK
        answer_val = _find_answer_value(rule.field_key, answers)
        if answer_val is not None:
            cand_rank = EDUCATION_RANK.get(str(answer_val).lower().replace(".", "").replace(" ", ""), 0)
            req_rank = EDUCATION_RANK.get(target.lower().replace(".", "").replace(" ", ""), 0)
            if cand_rank == 0 or req_rank == 0:
                return True
            return _compare_numeric(cand_rank, req_rank, operator)
        return True

    # --- Boolean type (yes/no, true/false, bersedia/tidak) ---
    if rule_type == "boolean":
        answer_val = _find_answer_value(rule.field_key, answers)
        if answer_val is not None:
            answer_normalized = str(answer_val).lower().strip()
            target_normalized = target.lower().strip()
            truthy = {"yes", "true", "ya", "bersedia", "iya", "1"}
            falsy = {"no", "false", "tidak", "0"}
            answer_bool = answer_normalized in truthy
            target_bool = target_normalized in truthy
            if operator in ("eq", "=", "=="):
                return answer_bool == target_bool
            if operator in ("neq", "!=", "<>"):
                return answer_bool != target_bool
        return True

    # --- Range / numeric type ---
    if rule_type == "range":
        answer_val = _find_answer_value(rule.field_key, answers)
        if answer_val is not None:
            try:
                val = float(answer_val)
                req = float(target)
                return _compare_numeric(val, req, operator)
            except (ValueError, TypeError):
                pass
        return True

    # Default: tidak dikenal → beri lulus
    return True


def _find_answer_value(field_key: str | None, answers: list):
    """Cari nilai dari application answers berdasarkan field_key."""
    if not field_key or not answers:
        return None
    for answer in answers:
        fk = None
        if hasattr(answer, "form_field") and answer.form_field:
            fk = answer.form_field.field_key
        elif hasattr(answer, "field_key"):
            fk = answer.field_key
        if fk == field_key:
            # Ambil nilai yang tersedia
            if hasattr(answer, "value_text") and answer.value_text is not None:
                return answer.value_text
            if hasattr(answer, "value_number") and answer.value_number is not None:
                return answer.value_number
    return None


def _compare_numeric(value: float, target: float, operator: str) -> bool:
    """Bandingkan dua nilai numerik berdasarkan operator."""
    op_map = {
        "eq": value == target,
        "=": value == target,
        "==": value == target,
        "neq": value != target,
        "!=": value != target,
        "gt": value > target,
        ">": value > target,
        "gte": value >= target,
        ">=": value >= target,
        "lt": value < target,
        "<": value < target,
        "lte": value <= target,
        "<=": value <= target,
    }
    return op_map.get(operator, True)



def _score_experience(years: int, required: str) -> float:
    try:
        req = int(required)
    except (ValueError, TypeError):
        req = 0
    if req <= 0:
        return 100.0
    if years >= req:
        return 100.0
    return (years / req) * 100.0


def _score_education(candidate_edu: list, required: str) -> float:
    if not required:
        return 100.0
    if not candidate_edu:
        return 0.0
    req_rank = EDUCATION_RANK.get(required.lower().replace(".", "").replace(" ", ""), 1)
    cand_rank = 1
    for e in candidate_edu:
        level = str(e.get("level", "")).lower().replace(".", "").replace(" ", "")
        cand_rank = max(cand_rank, EDUCATION_RANK.get(level, 1))
    if cand_rank >= req_rank:
        return 100.0
    return (cand_rank / req_rank) * 100.0


def _score_portfolio(parsed: dict) -> float:
    has_github = bool(parsed.get("github_url"))
    has_portfolio = bool(parsed.get("portfolio_url"))
    has_live = bool(parsed.get("live_project_url"))
    if has_github and has_live:
        return 100.0
    if has_github:
        return 75.0
    if has_portfolio:
        return 60.0
    return 0.0
