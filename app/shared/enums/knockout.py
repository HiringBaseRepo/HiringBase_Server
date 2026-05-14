"""Knockout-related enums."""
from enum import Enum


class KnockoutRuleType(str, Enum):
    DOCUMENT = "document"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    BOOLEAN = "boolean"
    RANGE = "range"


class KnockoutOperator(str, Enum):
    EQ = "eq"
    NEQ = "neq"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"


class KnockoutAction(str, Enum):
    AUTO_REJECT = "auto_reject"
    PENDING_REVIEW = "pending_review"
