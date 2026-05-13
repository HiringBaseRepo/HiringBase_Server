"""Scoring engine for the HiringBase application."""

from typing import List, Any

from app.shared.constants.scoring import MINIMUM_PASS_SCORE


def score_experience(total_years_experience: int, requirement: str) -> float:
    """Calculate experience score based on total years of experience and requirement."""
    required_years = int(requirement)
    if required_years == 0:
        return 100.0
    return min(100.0, (total_years_experience / required_years) * 100.0)


def score_education(education_level: List[Any], requirement: str) -> float:
    """Calculate education score based on education level and requirement."""
    from app.shared.constants.scoring import EDUCATION_RANK

    if not requirement:
        return 100.0
    if not education_level:
        return 0.0
    
    # Normalize requirement
    req_key = str(requirement).lower().replace(".", "").replace(" ", "").strip()
    required_rank = EDUCATION_RANK.get(req_key, 1)
    
    # Extract levels and get max rank
    levels = []
    for item in education_level:
        if isinstance(item, dict):
            levels.append(str(item.get("level", "")).lower().replace(".", "").replace(" ", "").strip())
        else:
            levels.append(str(item).lower().replace(".", "").replace(" ", "").strip())

    candidate_rank = max(EDUCATION_RANK.get(level, 1) for level in levels) if levels else 1
    
    if candidate_rank >= required_rank:
        return 100.0
    return min(100.0, (candidate_rank / required_rank) * 100.0)


def score_portfolio(parsed_data: dict) -> float:
    """Calculate portfolio score based on parsed data."""
    portfolio_fields = [
        "github_url",
        "portfolio_url",
        "live_project_url",
    ]
    score = 0.0
    for field in portfolio_fields:
        if parsed_data.get(field):
            score += 33.33
    return min(100.0, score)


def calculate_final_score(
    skill_match_score: float,
    experience_score: float,
    education_score: float,
    portfolio_score: float,
    soft_skill_score: float,
    administrative_score: float = 100.0,
    skill_match_weight: float = 40.0,
    experience_weight: float = 20.0,
    education_weight: float = 10.0,
    portfolio_weight: float = 10.0,
    soft_skill_weight: float = 10.0,
    administrative_weight: float = 10.0,
) -> float:
    """Calculate final score based on weighted scores."""
    final = (
        skill_match_score * skill_match_weight
        + experience_score * experience_weight
        + education_score * education_weight
        + portfolio_score * portfolio_weight
        + soft_skill_score * soft_skill_weight
        + administrative_score * administrative_weight
    ) / 100.0
    return final


def get_application_status(final_score: float) -> str:
    """Determine application status based on final score."""
    from app.shared.enums.application_status import ApplicationStatus

    return (
        ApplicationStatus.AI_PASSED
        if final_score >= MINIMUM_PASS_SCORE
        else ApplicationStatus.UNDER_REVIEW
    )
