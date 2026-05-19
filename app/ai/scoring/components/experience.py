"""Experience component scoring."""

from typing import Any

from app.shared.constants.scoring import (
    DEFAULT_COMPONENT_RUBRICS,
    NEUTRAL_ANCHORED_RATING,
    anchored_rating_to_score,
)
from app.ai.scoring.utils import (
    estimate_relevance_score,
    extract_category_requirements,
    extract_numeric_requirement,
    extract_requirement_terms,
    safe_rating_from_score,
)


def build_experience_component(parsed_data: dict[str, Any], requirements: list[Any]) -> dict[str, Any]:
    experience_requirements = extract_category_requirements(requirements, "experience")
    candidate_years = int(parsed_data.get("total_years_experience", 0) or 0)
    required_years = extract_numeric_requirement(experience_requirements)
    relevance_terms = extract_requirement_terms(experience_requirements)
    candidate_blob = " ".join(
        filter(
            None,
            [
                parsed_data.get("experience_domain"),
                parsed_data.get("experience_role_text"),
                parsed_data.get("experience_summary"),
            ],
        )
    )

    if required_years is None and not relevance_terms:
        raw_score = anchored_rating_to_score(NEUTRAL_ANCHORED_RATING)
    else:
        years_score = (
            100.0
            if required_years in (None, 0)
            else min(100.0, (candidate_years / required_years) * 100.0)
        )
        relevance_score = estimate_relevance_score(candidate_blob, relevance_terms)
        raw_score = (years_score * 0.7) + (relevance_score * 0.3)

    rating = safe_rating_from_score(raw_score)
    return {
        "score": anchored_rating_to_score(rating),
        "rating": rating,
        "rubric": DEFAULT_COMPONENT_RUBRICS["experience"][rating],
        "raw_score": round(raw_score, 2),
        "confidence": 0.85 if experience_requirements else 0.6,
        "required_years": required_years,
        "evidence": {
            "candidate_years": candidate_years,
            "experience_domain": parsed_data.get("experience_domain"),
            "experience_role_text": parsed_data.get("experience_role_text"),
            "requirement_terms": relevance_terms,
        },
    }
