"""Notification schemas."""
from pydantic import BaseModel
from app.shared.enums.notification_type import NotificationType


class NotificationItem(BaseModel):
    id: int
    type: NotificationType
    title: str
    message: str
    is_read: bool
    read_at: str | None
    created_at: str | None
    entity_type: str
    entity_id: int | None


class NotificationSummaryResponse(BaseModel):
    unread_count: int


class NotificationReadResponse(BaseModel):
    notification_id: int
    read: bool
    read_at: str | None


class NotificationReadAllResponse(BaseModel):
    read_all: bool
    updated_count: int
    read_at: str | None
