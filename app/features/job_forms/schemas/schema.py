"""Job form schemas."""
from pydantic import BaseModel

from app.shared.enums.field_type import FormFieldType


class CreateFormFieldRequest(BaseModel):
    field_key: str
    field_type: FormFieldType
    label: str
    placeholder: str | None = None
    help_text: str | None = None
    options: dict | None = None
    is_required: bool = True
    order_index: int = 0
    validation_rules: dict | None = None


class FormFieldCreatedResponse(BaseModel):
    field_id: int
    field_key: str


class FormFieldUpdatedResponse(BaseModel):
    field_id: int
    updated: bool


class FormFieldDeletedResponse(BaseModel):
    deleted: bool


class FormFieldOrderItem(BaseModel):
    field_id: int
    order_index: int


class ReorderFieldsRequest(BaseModel):
    order: list[FormFieldOrderItem]


class ReorderFieldsResponse(BaseModel):
    reordered: bool
