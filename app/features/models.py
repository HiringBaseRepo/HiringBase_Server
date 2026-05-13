"""
Database Models Aggregator — HiringBase
This file serves as a central registry for all domain-specific models.
It enables Alembic to discover all models through a single import point.
"""
from datetime import datetime, timezone

# Re-export models from feature-based modules

def now_utc() -> datetime:
    """Helper to get current time in UTC, preserved for backward compatibility."""
    return datetime.now(timezone.utc)
