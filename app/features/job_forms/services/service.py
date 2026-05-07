"""Job form business logic."""
from app.core.exceptions import FieldNotFoundException
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.job_forms.repositories.repository import (
    delete_form_field as delete_form_field_query,
    get_form_field,
    save_form_field,
    update_field_order,
)
from app.features.job_forms.schemas.schema import (
    CreateFormFieldRequest,
    FormFieldCreatedResponse,
    FormFieldDeletedResponse,
    FormFieldUpdatedResponse,
    ReorderFieldsRequest,
    ReorderFieldsResponse,
)
from app.features.jobs.models import JobFormField


async def create_form_field(
    db: AsyncSession,
    *,
    job_id: int,
    data: CreateFormFieldRequest,
) -> FormFieldCreatedResponse:
    field = JobFormField(
        job_id=job_id,
        field_key=data.field_key,
        field_type=data.field_type,
        label=data.label,
        placeholder=data.placeholder,
        help_text=data.help_text,
        options=data.options,
        is_required=data.is_required,
        order_index=data.order_index,
        validation_rules=data.validation_rules,
    )
    field = await save_form_field(db, field)
    await db.commit()
    return FormFieldCreatedResponse(field_id=field.id, field_key=field.field_key)


async def update_form_field(
    db: AsyncSession,
    *,
    job_id: int,
    field_id: int,
    updates: dict,
) -> FormFieldUpdatedResponse:
    field = await get_form_field(db, job_id=job_id, field_id=field_id)
    if not field:
        raise FieldNotFoundException()
    for key, value in updates.items():
        if hasattr(field, key):
            setattr(field, key, value)
    await db.commit()
    return FormFieldUpdatedResponse(field_id=field.id, updated=True)


async def delete_form_field(
    db: AsyncSession,
    *,
    job_id: int,
    field_id: int,
) -> FormFieldDeletedResponse:
    field = await get_form_field(db, job_id=job_id, field_id=field_id)
    if not field:
        raise FieldNotFoundException()
    await delete_form_field_query(db, field)
    await db.commit()
    return FormFieldDeletedResponse(deleted=True)


async def reorder_fields(
    db: AsyncSession,
    *,
    job_id: int,
    data: ReorderFieldsRequest,
) -> ReorderFieldsResponse:
    for item in data.order:
        await update_field_order(db, job_id=job_id, field_id=item.field_id, order_index=item.order_index)
    await db.commit()
    return ReorderFieldsResponse(reordered=True)
