"""Candidate data parser for screening service."""

from typing import Any

from app.features.screening.services.helpers import find_answer_value


def build_candidate_profile(application: Any, answers: list[Any]) -> dict[str, Any]:
    """Build candidate profile from form answers.

    Args:
        application: Application object containing applicant details
        answers: List of application answers

    Returns:
        Dictionary containing parsed candidate data
    """
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


def _score_experience(years: int, required: str) -> float:
    """Score experience based on years and requirements.

    Args:
        years: Years of experience
        required: Required years as string

    Returns:
        Experience score (0-100)
    """
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
    """Score education based on candidate education and requirements.

    Args:
        candidate_edu: List of candidate education entries
        required: Required education level

    Returns:
        Education score (0-100)
    """
    from app.shared.constants.scoring import EDUCATION_RANK

    if not required:
        return 100.0
    if not candidate_edu:
        return 0.0
    req_rank = EDUCATION_RANK.get(required.lower().replace(".", "").replace(" ", ""), 1)
    cand_rank = 1
    for item in candidate_edu:
        level = str(item.get("level", "")).lower().replace(".", "").replace(" ", "")
        cand_rank = max(cand_rank, EDUCATION_RANK.get(level, 1))
    if cand_rank >= req_rank:
        return 100.0
    return (cand_rank / req_rank) * 100.0


def _score_portfolio(parsed: dict) -> float:
    """Score portfolio based on provided URLs.

    Args:
        parsed: Parsed candidate data

    Returns:
        Portfolio score (0-100)
    """
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


def _clamp_score(value: float) -> float:
    """Clamp score value between 0 and 100.

    Args:
        value: Score value

    Returns:
        Clamped score value
    """
    return max(0, min(100, value))
