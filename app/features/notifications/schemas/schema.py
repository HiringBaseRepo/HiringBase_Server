"""Notification schemas."""
from pydantic import BaseModel


class NotificationItem(BaseModel):
    id: int
    type: str
    title: str
    message: str
    is_read: bool
    created_at: str | None


class NotificationReadResponse(BaseModel):
    read: bool


class NotificationReadAllResponse(BaseModel):
    read_all: bool
