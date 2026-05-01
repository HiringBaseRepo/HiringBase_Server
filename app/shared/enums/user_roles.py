"""User roles enum."""
from enum import Enum


class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    HR = "hr"
    APPLICANT = "applicant"
