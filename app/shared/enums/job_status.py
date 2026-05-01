"""Vacancy publication status."""
from enum import Enum


class JobStatus(str, Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    CLOSED = "closed"
    PRIVATE = "private"
