"""Skill component scoring."""

from typing import Any

from app.shared.constants.scoring import (
    DEFAULT_COMPONENT_RUBRICS,
    LOW_CONFIDENCE_THRESHOLD,
    anchored_rating_to_score,
)
from app.ai.scoring.utils import safe_rating_from_score


def build_skill_component(match_result: dict[str, Any]) -> dict[str, Any]:
    match_percentage = float(match_result.get("match_percentage", 0.0))
    insufficient_requirements = bool(match_result.get("insufficient_requirements"))
    confidence_score = float(match_result.get("confidence_score", 0.0))

    if insufficient_requirements:
        rating = 1
        score = anchored_rating_to_score(rating)
    else:
        rating = safe_rating_from_score(match_percentage)
        score = anchored_rating_to_score(rating)

    return {
        "score": score,
        "rating": rating,
        "rubric": DEFAULT_COMPONENT_RUBRICS["skill_match"][rating],
        "raw_score": round(match_percentage, 2),
        "confidence": confidence_score,
        "requirement_count": int(match_result.get("requirement_count", 0)),
        "gate_low_confidence": confidence_score < LOW_CONFIDENCE_THRESHOLD,
        "insufficient_requirements": insufficient_requirements,
        "evidence": {
            "matched_skills": match_result.get("matched_skills", []),
            "missing_skills": match_result.get("missing_skills", []),
        },
    }
