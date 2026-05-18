"""Scoring engine for the HiringBase application."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from app.shared.constants.scoring import (
    DEFAULT_WEIGHTS,
    DEFAULT_COMPONENT_RUBRICS,
    EDUCATION_RANK,
    LOW_CONFIDENCE_THRESHOLD,
    MINIMUM_PASS_SCORE,
    NEUTRAL_ANCHORED_RATING,
    anchored_rating_to_score,
    parse_requirement_value,
    score_to_anchored_rating,
)


def _normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def _extract_category_requirements(requirements: list[Any], category: str) -> list[Any]:
    extracted: list[Any] = []
    for requirement in requirements:
        req_category = getattr(requirement, "category", None)
        if req_category == category:
            extracted.append(requirement)
        elif isinstance(requirement, dict) and requirement.get("category") == category:
            extracted.append(requirement)
    return extracted


def _get_requirement_name(requirement: Any) -> str:
    if hasattr(requirement, "name"):
        return str(requirement.name or "").strip()
    if isinstance(requirement, dict):
        return str(requirement.get("name", "")).strip()
    return ""


def _get_requirement_value(requirement: Any) -> Any:
    if hasattr(requirement, "value"):
        return requirement.value
    if isinstance(requirement, dict):
        return requirement.get("value")
    return None


def _extract_numeric_requirement(requirements: list[Any]) -> int | None:
    for requirement in requirements:
        payload = parse_requirement_value(_get_requirement_value(requirement))
        candidates = [
            payload.get("years"),
            payload.get("minimum_years"),
            payload.get("min_years"),
            payload.get("value"),
            _get_requirement_value(requirement),
        ]
        for candidate in candidates:
            if candidate in (None, ""):
                continue
            try:
                return int(float(candidate))
            except (TypeError, ValueError):
                continue
    return None


def _extract_education_requirement(requirements: list[Any]) -> dict[str, str | None]:
    for requirement in requirements:
        payload = parse_requirement_value(_get_requirement_value(requirement))
        level = payload.get("level") or payload.get("degree") or payload.get("value")
        major = (
            payload.get("major")
            or payload.get("field")
            or payload.get("study_program")
            or _get_requirement_name(requirement)
        )
        return {
            "level": str(level).strip() if level not in (None, "") else None,
            "major": str(major).strip() if major not in (None, "") else None,
        }
    return {"level": None, "major": None}


def _extract_requirement_terms(requirements: list[Any]) -> list[str]:
    terms: list[str] = []
    for requirement in requirements:
        payload = parse_requirement_value(_get_requirement_value(requirement))
        sources = [
            _get_requirement_name(requirement),
            payload.get("domain"),
            payload.get("role"),
            payload.get("major"),
            payload.get("field"),
            payload.get("keywords"),
            payload.get("value"),
        ]
        for source in sources:
            if isinstance(source, list):
                terms.extend([_normalize_text(item) for item in source if _normalize_text(item)])
            else:
                normalized = _normalize_text(source)
                if normalized:
                    terms.append(normalized)
    return list(dict.fromkeys(terms))


def _estimate_relevance_score(candidate_blob: str, requirement_terms: list[str]) -> float:
    if not requirement_terms:
        return anchored_rating_to_score(NEUTRAL_ANCHORED_RATING)

    if not candidate_blob.strip():
        return 40.0

    normalized_blob = _normalize_text(candidate_blob)
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


def _safe_rating_from_score(score: float) -> int:
    return score_to_anchored_rating(max(0.0, min(100.0, score)))


def build_skill_component(match_result: dict[str, Any]) -> dict[str, Any]:
    match_percentage = float(match_result.get("match_percentage", 0.0))
    insufficient_requirements = bool(match_result.get("insufficient_requirements"))
    confidence_score = float(match_result.get("confidence_score", 0.0))

    if insufficient_requirements:
        rating = 1
        score = anchored_rating_to_score(rating)
    else:
        rating = _safe_rating_from_score(match_percentage)
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


def build_experience_component(parsed_data: dict[str, Any], requirements: list[Any]) -> dict[str, Any]:
    experience_requirements = _extract_category_requirements(requirements, "experience")
    candidate_years = int(parsed_data.get("total_years_experience", 0) or 0)
    required_years = _extract_numeric_requirement(experience_requirements)
    relevance_terms = _extract_requirement_terms(experience_requirements)
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
        relevance_score = _estimate_relevance_score(candidate_blob, relevance_terms)
        raw_score = (years_score * 0.7) + (relevance_score * 0.3)

    rating = _safe_rating_from_score(raw_score)
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


def build_education_component(parsed_data: dict[str, Any], requirements: list[Any]) -> dict[str, Any]:
    education_requirements = _extract_category_requirements(requirements, "education")
    education_items = parsed_data.get("education", [])
    candidate_major = _normalize_text(parsed_data.get("education_major"))
    requirement = _extract_education_requirement(education_requirements)

    if not requirement["level"] and not requirement["major"]:
        raw_score = anchored_rating_to_score(NEUTRAL_ANCHORED_RATING)
    else:
        candidate_levels = []
        for item in education_items:
            if isinstance(item, dict):
                candidate_levels.append(_normalize_text(item.get("level")))
            else:
                candidate_levels.append(_normalize_text(item))

        candidate_rank = max((EDUCATION_RANK.get(level, 1) for level in candidate_levels), default=1)
        required_level = _normalize_text(requirement["level"])
        required_rank = EDUCATION_RANK.get(required_level, 1) if required_level else 0

        if required_rank == 0:
            level_score = anchored_rating_to_score(NEUTRAL_ANCHORED_RATING)
        elif candidate_rank >= required_rank:
            level_score = 100.0
        else:
            level_score = min(100.0, (candidate_rank / required_rank) * 100.0)

        major_terms = [_normalize_text(requirement["major"])] if requirement["major"] else []
        major_score = _estimate_relevance_score(candidate_major, major_terms)
        raw_score = (level_score * 0.7) + (major_score * 0.3)

    rating = _safe_rating_from_score(raw_score)
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


def _normalize_url(value: Any) -> str | None:
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


def build_portfolio_component(parsed_data: dict[str, Any], requirements: list[Any]) -> dict[str, Any]:
    required_skills = _extract_category_requirements(requirements, "skill")
    valid_urls = []
    for raw_value in parsed_data.get("portfolio_urls", []):
        normalized = _normalize_url(raw_value)
        if normalized and normalized not in valid_urls:
            valid_urls.append(normalized)

    portfolio_evidence = _normalize_text(parsed_data.get("portfolio_evidence"))
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

    requirement_terms = _extract_requirement_terms(required_skills)
    evidence_blob = " ".join(filter(None, [portfolio_evidence, parsed_data.get("skills") and " ".join(parsed_data["skills"])]))
    relevance_score = _estimate_relevance_score(evidence_blob, requirement_terms)
    raw_score = (base_score * 0.8) + (relevance_score * 0.2)

    rating = _safe_rating_from_score(raw_score)
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


def build_soft_skill_component(
    soft_skill_payload: dict[str, Any],
    text: str,
    text_answer_count: int,
) -> dict[str, Any]:
    composite_score = float(soft_skill_payload.get("composite_score", 0.0))
    text_length = len(text.strip())
    evidence_quality = 100.0
    if text_answer_count <= 1:
        evidence_quality = 50.0
    elif text_answer_count == 2:
        evidence_quality = 70.0
    if text_length < 120:
        evidence_quality = min(evidence_quality, 50.0)
    elif text_length < 250:
        evidence_quality = min(evidence_quality, 70.0)

    raw_score = (composite_score * 0.7) + (evidence_quality * 0.3)
    rating = _safe_rating_from_score(raw_score)
    return {
        "score": anchored_rating_to_score(rating),
        "rating": rating,
        "rubric": DEFAULT_COMPONENT_RUBRICS["soft_skill"][rating],
        "raw_score": round(raw_score, 2),
        "confidence": 0.8 if text_length >= 120 else 0.6,
        "evidence": {
            "dimensions": {
                "communication": soft_skill_payload.get("communication"),
                "leadership": soft_skill_payload.get("leadership"),
                "teamwork": soft_skill_payload.get("teamwork"),
                "problem_solving": soft_skill_payload.get("problem_solving"),
                "initiative": soft_skill_payload.get("initiative"),
            },
            "text_answer_count": text_answer_count,
            "text_length": text_length,
            "evidence_quality": round(evidence_quality, 2),
        },
    }


def build_administrative_component(
    document_count: int,
    requirements: list[Any],
    doc_validation_flags: list[dict[str, Any]],
) -> dict[str, Any]:
    required_document_requirements = _extract_category_requirements(requirements, "document")
    required_document_count = len(required_document_requirements)
    has_required_documents = required_document_count > 0

    if any(flag.get("risk_level") == "high" for flag in doc_validation_flags if isinstance(flag, dict)):
        raw_score = 20.0
    elif doc_validation_flags:
        raw_score = 60.0
    elif not has_required_documents and document_count == 0:
        raw_score = 100.0
    elif has_required_documents and document_count >= required_document_count:
        raw_score = 100.0
    elif document_count > 0:
        raw_score = 60.0
    else:
        raw_score = 20.0

    rating = _safe_rating_from_score(raw_score)
    return {
        "score": anchored_rating_to_score(rating),
        "rating": rating,
        "rubric": DEFAULT_COMPONENT_RUBRICS["administrative"][rating],
        "raw_score": round(raw_score, 2),
        "confidence": 0.9,
        "evidence": {
            "document_count": document_count,
            "required_document_count": required_document_count,
            "validation_flags": doc_validation_flags,
        },
    }


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
        "administrative": build_administrative_component(
            document_count,
            requirements,
            doc_validation_flags,
        ),
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
