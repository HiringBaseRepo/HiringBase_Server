"""Education component scoring."""

from typing import Any

from app.shared.constants.scoring import (
    DEFAULT_COMPONENT_RUBRICS,
    EDUCATION_RANK,
    NEUTRAL_ANCHORED_RATING,
    anchored_rating_to_score,
)
from app.ai.scoring.utils import (
    estimate_relevance_score,
    extract_category_requirements,
    extract_education_requirement,
    normalize_text,
    safe_rating_from_score,
)


def build_education_component(parsed_data: dict[str, Any], requirements: list[Any]) -> dict[str, Any]:
    education_requirements = extract_category_requirements(requirements, "education")
    education_items = parsed_data.get("education", [])
    candidate_major = normalize_text(parsed_data.get("education_major"))
    requirement = extract_education_requirement(education_requirements)

    if not requirement["level"] and not requirement["major"]:
        raw_score = anchored_rating_to_score(NEUTRAL_ANCHORED_RATING)
    else:
        candidate_levels = []
        for item in education_items:
            if isinstance(item, dict):
                candidate_levels.append(normalize_text(item.get("level")))
            else:
                candidate_levels.append(normalize_text(item))

        candidate_rank = max((EDUCATION_RANK.get(level, 1) for level in candidate_levels), default=1)
        required_level = normalize_text(requirement["level"])
        required_rank = EDUCATION_RANK.get(required_level, 1) if required_level else 0

        if required_rank == 0:
            level_score = anchored_rating_to_score(NEUTRAL_ANCHORED_RATING)
        elif candidate_rank >= required_rank:
            level_score = 100.0
        else:
            level_score = min(100.0, (candidate_rank / required_rank) * 100.0)

        major_terms = [normalize_text(requirement["major"])] if requirement["major"] else []
        major_score = estimate_relevance_score(candidate_major, major_terms)
        raw_score = (level_score * 0.7) + (major_score * 0.3)

    rating = safe_rating_from_score(raw_score)
    return {
        "score": anchored_rating_to_score(rating),
        "rating": rating,
        "rubric": DEFAULT_COMPONENT_RUBRICS["education"][rating],
        "raw_score": round(raw_score, 2),
        "confidence": 0.85 if education_requirements else 0.6,
        "evidence": {
            "candidate_education": education_items,
            "candidate_major": parsed_data.get("education_major"),
            "required_level": requirement["level"],
            "required_major": requirement["major"],
        },
    }
