"""Screening schemas."""

from pydantic import BaseModel
from typing import List
from app.shared.enums.knockout import KnockoutAction, KnockoutOperator, KnockoutRuleType


class KnockoutRuleCreateCommand(BaseModel):
    job_id: int
    rule_name: str
    rule_type: KnockoutRuleType
    operator: KnockoutOperator
    target_value: str
    field_key: str | None = None
    action: KnockoutAction = KnockoutAction.AUTO_REJECT


class KnockoutRuleCreatedResponse(BaseModel):
    rule_id: int
    job_id: int


class KnockoutRuleDeletedResponse(BaseModel):
    deleted: bool


class ScreeningQueuedResponse(BaseModel):
    message: str
    queue_status: str = "queued"
    task_enqueued: bool = True


class ManualOverrideResponse(BaseModel):
    application_id: int
    new_final_score: float
    is_manual_override: bool

class BatchScreeningRequest(BaseModel):
    application_ids: List[int]

class BatchScreeningItem(BaseModel):
    application_id: int
    queue_status: str
    task_enqueued: bool

class BatchScreeningResponse(BaseModel):
    total: int
    queued: int
    duplicates: int
    quota_blocked: int
    results: List[BatchScreeningItem]
