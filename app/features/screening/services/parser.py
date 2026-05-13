"""Candidate data parser for screening service."""

from typing import Any
import json
import structlog

from app.features.screening.services.helpers import find_answer_value

logger = structlog.get_logger(__name__)

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

    parsed_data = {
        "name": application.applicant.full_name if application.applicant else None,
        "email": application.applicant.email if application.applicant else None,
        "phone": application.applicant.phone if application.applicant else None,
        "skills": [],
        "education": [],
        "total_years_experience": 0,
        "github_url": find_answer_value("github_url", answers),
        "portfolio_url": find_answer_value("portfolio_url", answers),
        "live_project_url": find_answer_value("live_project_url", answers),
    }

    # Extract skills
    skills_raw = find_answer_value("skills", answers)
    if skills_raw:
        parsed_data["skills"] = [
            s.strip().lower() for s in str(skills_raw).split(",") if s.strip()
        ]

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
            {"level": str(edu_level).lower(), "raw": str(edu_level)}
        ]

    return parsed_data


async def _score_soft_skills(text: str, force_fallback: bool = False) -> float:
    """Score soft skills based on text analysis.

    Args:
        text: Combined text from all form answers
        force_fallback: If True, uses keyword-based scoring only.

    Returns:
        Soft skill score (0-100)
    """
    try:
        from app.ai.nlp.soft_skill_scorer import score_soft_skills

        res = await score_soft_skills(text, force_fallback=force_fallback)
        return res.get("composite_score", 60.0)
    except Exception:
        return 60.0
