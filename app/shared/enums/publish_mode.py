"""Job publish mode options."""
from enum import Enum


class PublishMode(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    SCHEDULED = "scheduled"
