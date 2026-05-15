"""Notification types."""
from enum import Enum


class NotificationType(str, Enum):
    NEW_APPLICATION = "new_application"
    SCREENING_PASSED = "screening_passed"
    SCREENING_UNDER_REVIEW = "screening_under_review"
    SCREENING_REJECTED = "screening_rejected"
    DOCUMENT_FAILED = "document_failed"
    INTERVIEW_SCHEDULED = "interview_scheduled"
    APPLICATION_OFFERED = "application_offered"
    APPLICATION_HIRED = "application_hired"
    APPLICATION_REJECTED = "application_rejected"
