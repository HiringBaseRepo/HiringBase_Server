"""Custom form field types."""
from enum import Enum


class FormFieldType(str, Enum):
    TEXT = "text"
    TEXTAREA = "textarea"
    NUMBER = "number"
    SELECT = "select"
    RADIO = "radio"
    CHECKBOX = "checkbox"
    DATE = "date"
    URL = "url"
    FILE = "file"
