"""Audit log schemas."""
from pydantic import BaseModel


class AuditLogItem(BaseModel):
    id: int
    action: str
    action_label: str | None = None
    entity_type: str
    entity_id: int
    old_values: dict | None
    new_values: dict | None
    created_at: str | None
