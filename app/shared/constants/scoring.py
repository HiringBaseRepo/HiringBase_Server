"""Scoring constants."""

DEFAULT_WEIGHTS = {
    "skill_match": 40,
    "experience": 20,
    "education": 10,
    "portfolio": 10,
    "soft_skill": 10,
    "administrative": 10,
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


def get_default_scoring_template() -> dict:
    """Return default scoring template weights."""
    return DEFAULT_WEIGHTS


KNOCKOUT_AUTO_REJECT = True

# Ticket format prefix
TICKET_PREFIX = "TKT"
TICKET_YEAR_FMT = "%Y"

# Job apply code prefix
APPLY_CODE_PREFIX = "FRM"
APPLY_CODE_LENGTH = 5
