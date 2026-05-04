"""
Database Models Aggregator — Smart Resume Screening System
This file serves as a central registry for all domain-specific models.
It enables Alembic to discover all models through a single import point.
"""
from datetime import datetime, timezone

# Re-export models from feature-based modules
from app.features.companies.models import Company
from app.features.users.models import User, RefreshToken
from app.features.jobs.models import Job, JobRequirement, JobScoringTemplate, JobFormField, JobKnockoutRule
from app.features.applications.models import Application, ApplicationAnswer, ApplicationDocument, ApplicationStatusLog
from app.features.screening.models import CandidateScore
from app.features.tickets.models import Ticket
from app.features.interviews.models import Interview
from app.features.notifications.models import Notification
from app.features.audit_logs.models import AuditLog

def now_utc() -> datetime:
    """Helper to get current time in UTC, preserved for backward compatibility."""
    return datetime.now(timezone.utc)
