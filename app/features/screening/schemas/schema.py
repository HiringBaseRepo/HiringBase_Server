"""Screening schemas."""
from pydantic import BaseModel


class KnockoutRuleCreateCommand(BaseModel):
    job_id: int
    rule_name: str
    rule_type: str
    operator: str
    target_value: str
    field_key: str | None = None
    action: str = "auto_reject"


class KnockoutRuleCreatedResponse(BaseModel):
    rule_id: int
    job_id: int


class KnockoutRuleDeletedResponse(BaseModel):
    deleted: bool


class ScreeningQueuedResponse(BaseModel):
    message: str


class ManualOverrideResponse(BaseModel):
    application_id: int
    new_final_score: float
    is_manual_override: bool
