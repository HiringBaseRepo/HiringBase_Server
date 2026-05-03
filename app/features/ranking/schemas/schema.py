"""Ranking schemas."""
from pydantic import BaseModel


class RankingItem(BaseModel):
    application_id: int
    applicant_name: str | None
    applicant_email: str | None
    status: str
    final_score: float | None
    skill_match: float | None
    experience: float | None
    education: float | None
    portfolio: float | None
    risk_level: str | None
    created_at: str | None
