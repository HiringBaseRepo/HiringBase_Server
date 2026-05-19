"""Scoring engine for the HiringBase application."""

from __future__ import annotations

from typing import Any

from app.shared.constants.scoring import (
    DEFAULT_WEIGHTS,
    EDUCATION_RANK,
    LOW_CONFIDENCE_THRESHOLD,
    MINIMUM_PASS_SCORE,
    NEUTRAL_ANCHORED_RATING,
    anchored_rating_to_score,
)
from app.ai.scoring.utils import normalize_text as _normalize_text
from app.ai.scoring.components.skill import build_skill_component
from app.ai.scoring.components.experience import build_experience_component
from app.ai.scoring.components.education import build_education_component
from app.ai.scoring.components.portfolio import build_portfolio_component
from app.ai.scoring.components.soft_skill import build_soft_skill_component
from app.ai.scoring.components.administrative import build_administrative_component


def build_scoring_breakdown(
    *,
    match_result: dict[str, Any],
    parsed_data: dict[str, Any],
    requirements: list[Any],
    soft_skill_payload: dict[str, Any],
    text: str,
    document_count: int,
    doc_validation_flags: list[dict[str, Any]],
) -> dict[str, Any]:
    components = {
        "skill_match": build_skill_component(match_result),
        "experience": build_experience_component(parsed_data, requirements),
        "education": build_education_component(parsed_data, requirements),
        "portfolio": build_portfolio_component(parsed_data, requirements),
        "soft_skill": build_soft_skill_component(
            soft_skill_payload,
            text,
            int(parsed_data.get("text_answer_count", 0) or 0),
        ),
        "administrative": build_administrative_component(document_count, doc_validation_flags),
    }

    gate_reasons: list[str] = []
    if components["skill_match"]["insufficient_requirements"]:
        gate_reasons.append("insufficient_structured_skill_requirements")
    if components["skill_match"]["gate_low_confidence"]:
        gate_reasons.append("low_skill_match_confidence")

    return {
        "components": components,
        "gates": {
            "force_under_review": bool(gate_reasons),
            "reasons": gate_reasons,
        },
    }


def score_experience(total_years_experience: int, requirement: str) -> float:
    """Backward-compatible experience score helper."""
    try:
        required_years = int(requirement)
    except (TypeError, ValueError):
        return anchored_rating_to_score(NEUTRAL_ANCHORED_RATING)

    if required_years == 0:
        return 100.0
    return min(100.0, (total_years_experience / required_years) * 100.0)


def score_education(education_level: list[Any], requirement: str) -> float:
    """Backward-compatible education score helper."""
    if not requirement:
        return anchored_rating_to_score(NEUTRAL_ANCHORED_RATING)
    if not education_level:
        return 20.0

    req_key = _normalize_text(requirement).replace(".", "").replace(" ", "")
    required_rank = EDUCATION_RANK.get(req_key, 1)
    levels = []
    for item in education_level:
        if isinstance(item, dict):
            levels.append(_normalize_text(item.get("level")).replace(".", "").replace(" ", ""))
        else:
            levels.append(_normalize_text(item).replace(".", "").replace(" ", ""))

    candidate_rank = max(EDUCATION_RANK.get(level, 1) for level in levels) if levels else 1
    if candidate_rank >= required_rank:
        return 100.0
    return min(100.0, (candidate_rank / required_rank) * 100.0)


def score_portfolio(parsed_data: dict) -> float:
    """Backward-compatible portfolio score helper."""
    return build_portfolio_component(parsed_data, []).get("raw_score", 20.0)


def calculate_final_score(
    skill_match_score: float,
    experience_score: float,
    education_score: float,
    portfolio_score: float,
    soft_skill_score: float,
    administrative_score: float = 100.0,
    skill_match_weight: float = DEFAULT_WEIGHTS["skill_match_weight"],
    experience_weight: float = DEFAULT_WEIGHTS["experience_weight"],
    education_weight: float = DEFAULT_WEIGHTS["education_weight"],
    portfolio_weight: float = DEFAULT_WEIGHTS["portfolio_weight"],
    soft_skill_weight: float = DEFAULT_WEIGHTS["soft_skill_weight"],
    administrative_weight: float = DEFAULT_WEIGHTS["administrative_weight"],
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
