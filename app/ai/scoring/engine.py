"""Scoring engine for the HiringBase application."""

from typing import List

from app.features.jobs.models import JobRequirement
from app.features.screening.models import CandidateScore
from app.shared.constants.scoring import MINIMUM_PASS_SCORE


def score_experience(total_years_experience: int, requirement: str) -> float:
    """Calculate experience score based on total years of experience and requirement."""
    required_years = int(requirement)
    if required_years == 0:
        return 100.0
    return min(100.0, (total_years_experience / required_years) * 100.0)


def score_education(education_level: List[str], requirement: str) -> float:
    """Calculate education score based on education level and requirement."""
    if not education_level:
        return 0.0
    # Map education levels to numerical values
    education_map = {
        "SMA": 1,
        "D3": 2,
        "S1": 3,
        "S2": 4,
        "S3": 5,
    }
    required_level = education_map.get(requirement, 0)
    candidate_level = max(education_map.get(level, 0) for level in education_level)
    if required_level == 0:
        return 100.0
    return min(100.0, (candidate_level / required_level) * 100.0)


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
