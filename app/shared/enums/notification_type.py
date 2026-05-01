"""Notification types."""
from enum import Enum


class NotificationType(str, Enum):
    APPLY_CONFIRMED = "apply_confirmed"
    AI_SCREENING_PASSED = "ai_screening_passed"
    INTERVIEW_INVITE = "interview_invite"
    OFFER_SENT = "offer_sent"
    HIRED = "hired"
    REJECTED = "rejected"
    DOC_MISSING = "doc_missing"
    KNOCKOUT_FAIL = "knockout_fail"
