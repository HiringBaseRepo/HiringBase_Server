"""Portfolio component scoring."""

from typing import Any

from app.shared.constants.scoring import (
    DEFAULT_COMPONENT_RUBRICS,
    anchored_rating_to_score,
)
from app.ai.scoring.utils import (
    estimate_relevance_score,
    extract_category_requirements,
    extract_requirement_terms,
    normalize_text,
    normalize_url,
    safe_rating_from_score,
)


def build_portfolio_component(parsed_data: dict[str, Any], requirements: list[Any]) -> dict[str, Any]:
    required_skills = extract_category_requirements(requirements, "skill")
    valid_urls = []
    for raw_value in parsed_data.get("portfolio_urls", []):
        normalized = normalize_url(raw_value)
        if normalized and normalized not in valid_urls:
            valid_urls.append(normalized)

    portfolio_evidence = normalize_text(parsed_data.get("portfolio_evidence"))
    base_score = 20.0
    if len(valid_urls) == 1:
        base_score = 60.0
    elif len(valid_urls) == 2:
        base_score = 80.0
    elif len(valid_urls) >= 3:
        base_score = 100.0

    if portfolio_evidence and len(portfolio_evidence) >= 40:
        base_score = min(100.0, base_score + 10.0)
    if parsed_data.get("live_project_url"):
        base_score = min(100.0, base_score + 10.0)

    requirement_terms = extract_requirement_terms(required_skills)
    evidence_blob = " ".join(filter(None, [portfolio_evidence, parsed_data.get("skills") and " ".join(parsed_data["skills"])]))
    relevance_score = estimate_relevance_score(evidence_blob, requirement_terms)
    raw_score = (base_score * 0.8) + (relevance_score * 0.2)

    rating = safe_rating_from_score(raw_score)
    return {
        "score": anchored_rating_to_score(rating),
        "rating": rating,
        "rubric": DEFAULT_COMPONENT_RUBRICS["portfolio"][rating],
        "raw_score": round(raw_score, 2),
        "confidence": 0.8 if valid_urls else 0.55,
        "evidence": {
            "valid_urls": valid_urls,
            "portfolio_evidence": parsed_data.get("portfolio_evidence"),
            "required_skill_terms": requirement_terms,
        },
    }
