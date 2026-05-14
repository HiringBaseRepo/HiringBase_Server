"""Scoring constants."""

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
