"""Scoring constants."""

from __future__ import annotations

from typing import Any

SKILL_MATCH_WEIGHT_KEY = "skill_match_weight"
EXPERIENCE_WEIGHT_KEY = "experience_weight"
EDUCATION_WEIGHT_KEY = "education_weight"
PORTFOLIO_WEIGHT_KEY = "portfolio_weight"
SOFT_SKILL_WEIGHT_KEY = "soft_skill_weight"
ADMINISTRATIVE_WEIGHT_KEY = "administrative_weight"

SCORING_WEIGHT_KEYS = (
    SKILL_MATCH_WEIGHT_KEY,
    EXPERIENCE_WEIGHT_KEY,
    EDUCATION_WEIGHT_KEY,
    PORTFOLIO_WEIGHT_KEY,
    SOFT_SKILL_WEIGHT_KEY,
    ADMINISTRATIVE_WEIGHT_KEY,
)

DEFAULT_WEIGHTS = {
    SKILL_MATCH_WEIGHT_KEY: 40,
    EXPERIENCE_WEIGHT_KEY: 20,
    EDUCATION_WEIGHT_KEY: 10,
    PORTFOLIO_WEIGHT_KEY: 10,
    SOFT_SKILL_WEIGHT_KEY: 10,
    ADMINISTRATIVE_WEIGHT_KEY: 10,
}

EDUCATION_RANK = {
    "sma": 1,
    "smk": 1,
    "d1": 2,
    "d2": 3,
    "d3": 4,
    "s1": 5,
    "s2": 6,
    "s3": 7,
    "profesi": 5,
}

MINIMUM_PASS_SCORE = 60.0
SOFT_SKILL_FALLBACK_SCORE = MINIMUM_PASS_SCORE
LOW_CONFIDENCE_THRESHOLD = 0.75
NEUTRAL_ANCHORED_RATING = 3

ANCHORED_RATING_TO_SCORE = {
    1: 20.0,
    2: 40.0,
    3: 60.0,
    4: 80.0,
    5: 100.0,
}

DEFAULT_COMPONENT_RUBRICS = {
    "skill_match": {
        5: "Structured skill requirement coverage is strong and confidence is high.",
        4: "Most structured skill requirements are covered with acceptable confidence.",
        3: "Partial skill coverage or moderate confidence requires review.",
        2: "Low skill coverage against structured requirements.",
        1: "Very weak skill evidence or missing structured requirements.",
    },
    "experience": {
        5: "Experience years and role/domain relevance strongly match job needs.",
        4: "Experience mostly aligns in years and relevance.",
        3: "Experience is adequate but only partially relevant or incomplete.",
        2: "Experience evidence is weak against structured requirement.",
        1: "Experience is insufficient or poorly aligned.",
    },
    "education": {
        5: "Education level and major/field strongly match requirement.",
        4: "Education level matches and field is reasonably relevant.",
        3: "Education is acceptable but relevance is limited or unclear.",
        2: "Education only partially meets level or field expectation.",
        1: "Education is weak or misaligned to requirement.",
    },
    "portfolio": {
        5: "Multiple valid portfolio evidences with strong relevance.",
        4: "Valid portfolio links exist and support candidate claims.",
        3: "Some portfolio evidence exists but depth/relevance is limited.",
        2: "Weak or thin portfolio evidence.",
        1: "No reliable portfolio evidence.",
    },
    "soft_skill": {
        5: "Soft skill evidence is strong across multiple dimensions.",
        4: "Soft skill evidence is good with enough written support.",
        3: "Soft skill signal is moderate and needs human review.",
        2: "Soft skill signal is weak or overly generic.",
        1: "Very low soft skill evidence.",
    },
    "administrative": {
        5: "Documents are complete and semantically clean.",
        4: "Documents are complete with minor non-blocking concerns.",
        3: "Documents are acceptable but have review-worthy issues.",
        2: "Documents have significant validation concerns.",
        1: "Administrative evidence is weak or high-risk.",
    },
}

EDUCATION_MAJOR_FIELD_KEYS = (
    "education_major",
    "major",
    "field_of_study",
    "study_program",
    "jurusan",
    "program_studi",
)

EXPERIENCE_DOMAIN_FIELD_KEYS = (
    "experience_domain",
    "industry_experience",
    "domain_experience",
    "experience_summary",
    "work_experience_summary",
)

EXPERIENCE_ROLE_FIELD_KEYS = (
    "current_role",
    "role_history",
    "last_role",
    "job_title",
    "position_applied_background",
)

PORTFOLIO_EVIDENCE_FIELD_KEYS = (
    "portfolio_description",
    "project_summary",
    "project_highlights",
    "achievement_summary",
)


def anchored_rating_to_score(rating: int) -> float:
    """Convert anchored rating 1-5 into deterministic 0-100 score."""
    safe_rating = max(1, min(5, int(rating)))
    return ANCHORED_RATING_TO_SCORE[safe_rating]


def score_to_anchored_rating(score: float) -> int:
    """Convert 0-100 score into anchored rating 1-5."""
    if score >= 90:
        return 5
    if score >= 75:
        return 4
    if score >= 55:
        return 3
    if score >= 35:
        return 2
    return 1


def parse_requirement_value(value: Any) -> dict[str, Any]:
    """Best-effort parse requirement text or JSON payload into dict."""
    if isinstance(value, dict):
        return value
    if value is None:
        return {}

    text = str(value).strip()
    if not text:
        return {}

    try:
        import json

        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    return {"value": text}


def get_default_scoring_template() -> dict:
    """Return default scoring template weights."""
    return dict(DEFAULT_WEIGHTS)


KNOCKOUT_AUTO_REJECT = True

# Ticket format prefix
TICKET_PREFIX = "TKT"
TICKET_YEAR_FMT = "%Y"

# Job apply code prefix
APPLY_CODE_PREFIX = "FRM"
APPLY_CODE_LENGTH = 5
