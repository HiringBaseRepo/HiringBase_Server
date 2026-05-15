"""Audit log schemas."""
from pydantic import BaseModel


class AuditLogItem(BaseModel):
    id: int
    action: str
    action_label: str | None = None
    entity_type: str
    entity_id: int
    user_name: str | None = None
    user_initials: str | None = None
    actor_type: str | None = None
    actor_role_label: str | None = None
    ip_address: str | None = None
    ip_address_display: str | None = None
    user_agent: str | None = None
    user_agent_display: str | None = None
    old_values: dict | None
    new_values: dict | None
    created_at: str | None
