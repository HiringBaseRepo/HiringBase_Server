"""Notification schemas."""
from pydantic import BaseModel
from app.shared.enums.notification_type import NotificationType


class NotificationItem(BaseModel):
    id: int
    type: NotificationType
    title: str
    message: str
    is_read: bool
    created_at: str | None


class NotificationReadResponse(BaseModel):
    read: bool


class NotificationReadAllResponse(BaseModel):
    read_all: bool
