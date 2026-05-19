"""Scoring utility functions."""

from typing import Any
from urllib.parse import urlparse

from app.shared.constants.scoring import (
    EDUCATION_RANK,
    NEUTRAL_ANCHORED_RATING,
    anchored_rating_to_score,
    parse_requirement_value,
    score_to_anchored_rating,
)


def normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def extract_category_requirements(requirements: list[Any], category: str) -> list[Any]:
    extracted: list[Any] = []
    for requirement in requirements:
        req_category = getattr(requirement, "category", None)
        if req_category == category:
            extracted.append(requirement)
        elif isinstance(requirement, dict) and requirement.get("category") == category:
            extracted.append(requirement)
    return extracted


def get_requirement_name(requirement: Any) -> str:
    if hasattr(requirement, "name"):
        return str(requirement.name or "").strip()
    if isinstance(requirement, dict):
        return str(requirement.get("name", "")).strip()
    return ""


def get_requirement_value(requirement: Any) -> Any:
    if hasattr(requirement, "value"):
        return requirement.value
    if isinstance(requirement, dict):
        return requirement.get("value")
    return None


def extract_numeric_requirement(requirements: list[Any]) -> int | None:
    for requirement in requirements:
        payload = parse_requirement_value(get_requirement_value(requirement))
        candidates = [
            payload.get("years"),
            payload.get("minimum_years"),
            payload.get("min_years"),
            payload.get("value"),
            get_requirement_value(requirement),
        ]
        for candidate in candidates:
            if candidate in (None, ""):
                continue
            try:
                return int(float(candidate))
            except (TypeError, ValueError):
                continue
    return None


def extract_education_requirement(requirements: list[Any]) -> dict[str, str | None]:
    for requirement in requirements:
        payload = parse_requirement_value(get_requirement_value(requirement))
        level = payload.get("level") or payload.get("degree") or payload.get("value")
        major = (
            payload.get("major")
            or payload.get("field")
            or payload.get("study_program")
            or get_requirement_name(requirement)
        )
        return {
            "level": str(level).strip() if level not in (None, "") else None,
            "major": str(major).strip() if major not in (None, "") else None,
        }
    return {"level": None, "major": None}


def extract_requirement_terms(requirements: list[Any]) -> list[str]:
    terms: list[str] = []
    for requirement in requirements:
        payload = parse_requirement_value(get_requirement_value(requirement))
        sources = [
            get_requirement_name(requirement),
            payload.get("domain"),
            payload.get("role"),
            payload.get("major"),
            payload.get("field"),
            payload.get("keywords"),
            payload.get("value"),
        ]
        for source in sources:
            if isinstance(source, list):
                terms.extend([normalize_text(item) for item in source if normalize_text(item)])
            else:
                normalized = normalize_text(source)
                if normalized:
                    terms.append(normalized)
    return list(dict.fromkeys(terms))


def estimate_relevance_score(candidate_blob: str, requirement_terms: list[str]) -> float:
    if not requirement_terms:
        return anchored_rating_to_score(NEUTRAL_ANCHORED_RATING)

    if not candidate_blob.strip():
        return 40.0

    normalized_blob = normalize_text(candidate_blob)
    exact_hits = [term for term in requirement_terms if term and term in normalized_blob]
    token_hits = set()
    for term in requirement_terms:
        for token in term.split():
            if len(token) >= 4 and token in normalized_blob:
                token_hits.add(token)

    if len(exact_hits) >= 2 or len(token_hits) >= 4:
        return 100.0
    if len(exact_hits) == 1 or len(token_hits) >= 2:
        return 80.0
    if token_hits:
        return 60.0
    return 40.0


def safe_rating_from_score(score: float) -> int:
    return score_to_anchored_rating(max(0.0, min(100.0, score)))


def normalize_url(value: Any) -> str | None:
    if value in (None, ""):
        return None
    raw = str(value).strip()
    if not raw:
        return None
    if "://" not in raw:
        raw = f"https://{raw}"
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return parsed.geturl()
