"""Candidate data parser for screening service."""

from typing import Any
import json
import structlog

from app.features.screening.services.helpers import find_answer_value
from app.shared.constants.scoring import (
    EDUCATION_MAJOR_FIELD_KEYS,
    EXPERIENCE_DOMAIN_FIELD_KEYS,
    EXPERIENCE_ROLE_FIELD_KEYS,
    PORTFOLIO_EVIDENCE_FIELD_KEYS,
    SOFT_SKILL_FALLBACK_SCORE,
)

logger = structlog.get_logger(__name__)


def _find_first_value(field_keys: tuple[str, ...], answers: list[Any]) -> Any:
    for field_key in field_keys:
        value = find_answer_value(field_key, answers)
        if value not in (None, ""):
            return value
    return None


def _normalize_text(value: Any) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    return text or None


def _parse_list_text(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return [str(item).strip().lower() for item in value if str(item).strip()]

    normalized = str(value).replace("\n", ",").replace(";", ",")
    return [item.strip().lower() for item in normalized.split(",") if item.strip()]


def _collect_text_blob(answers: list[Any]) -> str:
    text_parts: list[str] = []
    for answer in answers:
        value = getattr(answer, "value_text", None)
        if value:
            text_parts.append(str(value).strip())
    return "\n".join(text_parts)


def _count_non_empty_text_answers(answers: list[Any]) -> int:
    count = 0
    for answer in answers:
        if getattr(answer, "value_text", None):
            count += 1
    return count


def build_candidate_profile(application: Any, answers: list[Any]) -> dict[str, Any]:
    """Build candidate profile from form answers.

    Args:
        application: Application object containing applicant details
        answers: List of application answers

    Returns:
        Dictionary containing parsed candidate data
    """
    # Fallback for answers if list is empty but metadata exists
    if not answers and hasattr(application, "notes") and application.notes:
        try:
            notes_data = json.loads(application.notes)
            # Create mock answer objects for find_answer_value
            class MockAnswer:
                def __init__(self, key, val):
                    self.form_field = type('obj', (object,), {'field_key': key})
                    self.value_text = str(val)
                    self.value_number = None
                    self.value_json = None
            
            answers = [MockAnswer(k, v) for k, v in notes_data.items()]
            logger.debug(
                "parser_notes_fallback_used",
                answers_count=len(answers),
            )
        except (json.JSONDecodeError, TypeError):
            logger.warning("parser_notes_fallback_invalid_json")

    education_major = _normalize_text(_find_first_value(EDUCATION_MAJOR_FIELD_KEYS, answers))
    experience_domain = _normalize_text(_find_first_value(EXPERIENCE_DOMAIN_FIELD_KEYS, answers))
    experience_role_text = _normalize_text(_find_first_value(EXPERIENCE_ROLE_FIELD_KEYS, answers))
    portfolio_evidence = _normalize_text(_find_first_value(PORTFOLIO_EVIDENCE_FIELD_KEYS, answers))

    parsed_data = {
        "name": application.applicant.full_name if application.applicant else None,
        "email": application.applicant.email if application.applicant else None,
        "phone": application.applicant.phone if application.applicant else None,
        "skills": [],
        "education": [],
        "total_years_experience": 0,
        "education_major": education_major,
        "experience_domain": experience_domain,
        "experience_role_text": experience_role_text,
        "experience_summary": _normalize_text(
            find_answer_value("experience_summary", answers)
            or find_answer_value("work_experience_summary", answers)
            or experience_domain
        ),
        "portfolio_evidence": portfolio_evidence,
        "github_url": _normalize_text(find_answer_value("github_url", answers)),
        "portfolio_url": _normalize_text(find_answer_value("portfolio_url", answers)),
        "live_project_url": _normalize_text(find_answer_value("live_project_url", answers)),
        "text_answer_count": _count_non_empty_text_answers(answers),
        "text_blob": _collect_text_blob(answers),
    }

    # Extract skills
    skills_raw = find_answer_value("skills", answers)
    parsed_data["skills"] = _parse_list_text(skills_raw)

    # Extract experience years
    exp_years = find_answer_value("experience_years", answers)
    if exp_years:
        try:
            parsed_data["total_years_experience"] = int(float(exp_years))
        except (ValueError, TypeError):
            parsed_data["total_years_experience"] = 0

    # Extract education
    edu_level = find_answer_value("education_level", answers)
    if edu_level:
        parsed_data["education"] = [
            {
                "level": str(edu_level).lower(),
                "raw": str(edu_level),
                "major": education_major,
            }
        ]

    parsed_data["experience_keywords"] = _parse_list_text(experience_role_text)
    parsed_data["portfolio_urls"] = [
        value
        for value in [
            parsed_data["github_url"],
            parsed_data["portfolio_url"],
            parsed_data["live_project_url"],
        ]
        if value
    ]

    return parsed_data


async def _score_soft_skills(text: str, force_fallback: bool = False) -> dict[str, float]:
    """Score soft skills based on text analysis.

    Args:
        text: Combined text from all form answers
        force_fallback: If True, uses keyword-based scoring only.

    Returns:
        Soft skill score payload
    """
    try:
        from app.ai.nlp.soft_skill_scorer import score_soft_skills

        return await score_soft_skills(text, force_fallback=force_fallback)
    except Exception:
        return {
            "communication": SOFT_SKILL_FALLBACK_SCORE,
            "leadership": SOFT_SKILL_FALLBACK_SCORE,
            "teamwork": SOFT_SKILL_FALLBACK_SCORE,
            "problem_solving": SOFT_SKILL_FALLBACK_SCORE,
            "initiative": SOFT_SKILL_FALLBACK_SCORE,
            "composite_score": SOFT_SKILL_FALLBACK_SCORE,
        }
