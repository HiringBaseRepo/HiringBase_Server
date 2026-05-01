"""Application status lifecycle."""
from enum import Enum


class ApplicationStatus(str, Enum):
    APPLIED = "applied"
    DOC_CHECK = "doc_check"
    DOC_FAILED = "doc_failed"
    AI_PROCESSING = "ai_processing"
    AI_PASSED = "ai_passed"
    UNDER_REVIEW = "under_review"
    INTERVIEW = "interview"
    OFFERED = "offered"
    HIRED = "hired"
    REJECTED = "rejected"
    KNOCKOUT = "knockout"
