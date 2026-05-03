"""Scoring template schemas."""
from pydantic import BaseModel


class CreateScoringTemplateRequest(BaseModel):
    job_id: int
    skill_match_weight: int
    experience_weight: int
    education_weight: int
    portfolio_weight: int
    soft_skill_weight: int
    administrative_weight: int
    custom_rules: dict | None = None


class ScoringTemplateCreatedResponse(BaseModel):
    template_id: int
    job_id: int


class ScoringTemplateUpdateResponse(BaseModel):
    template_id: int
    updated: bool


class ScoringWeightsResponse(BaseModel):
    skill_match: int
    experience: int
    education: int
    portfolio: int
    soft_skill: int
    administrative: int


class ScoringTemplateResponse(BaseModel):
    template_id: int
    weights: ScoringWeightsResponse
    custom_rules: dict | None
