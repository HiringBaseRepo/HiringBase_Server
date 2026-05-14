"""Interview enums."""
from enum import Enum


class InterviewType(str, Enum):
    IN_PERSON = "in_person"
    VIDEO = "video"
    PHONE = "phone"


class InterviewResult(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    PENDING = "pending"
