"""Job form business logic."""
from app.core.exceptions import FieldNotFoundException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils.audit import get_model_snapshot
from app.features.audit_logs.models import AuditLog
from app.features.audit_logs.repositories.repository import create_audit_log
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
from app.features.users.models import User
from app.shared.constants.audit_actions import (
    JOB_FORM_FIELD_CREATE,
    JOB_FORM_FIELD_DELETE,
    JOB_FORM_FIELD_REORDER,
    JOB_FORM_FIELD_UPDATE,
)
from app.shared.constants.audit_entities import JOB_FORM_FIELD


async def create_form_field(
    db: AsyncSession,
    *,
    job_id: int,
    data: CreateFormFieldRequest,
    current_user: User,
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
    await create_audit_log(
        db,
        AuditLog(
            company_id=current_user.company_id,
            user_id=current_user.id,
            action=JOB_FORM_FIELD_CREATE,
            entity_type=JOB_FORM_FIELD,
            entity_id=field.id,
            new_values={
                "job_id": job_id,
                "field_key": field.field_key,
                "field_type": field.field_type.value,
                "is_required": field.is_required,
                "order_index": field.order_index,
            },
        ),
    )
    await db.commit()
    return FormFieldCreatedResponse(field_id=field.id, field_key=field.field_key)


async def update_form_field(
    db: AsyncSession,
    *,
    job_id: int,
    field_id: int,
    updates: dict,
    current_user: User,
) -> FormFieldUpdatedResponse:
    field = await get_form_field(db, job_id=job_id, field_id=field_id)
    if not field:
        raise FieldNotFoundException()

    old_values = get_model_snapshot(field)
    
    for key, value in updates.items():
        if hasattr(field, key):
            setattr(field, key, value)
            
    await create_audit_log(
        db,
        AuditLog(
            company_id=current_user.company_id,
            user_id=current_user.id,
            action=JOB_FORM_FIELD_UPDATE,
            entity_type=JOB_FORM_FIELD,
            entity_id=field.id,
            old_values=old_values,
            new_values=updates
        )
    )
    await db.commit()
    return FormFieldUpdatedResponse(field_id=field.id, updated=True)


async def delete_form_field(
    db: AsyncSession,
    *,
    job_id: int,
    field_id: int,
    current_user: User,
) -> FormFieldDeletedResponse:
    field = await get_form_field(db, job_id=job_id, field_id=field_id)
    if not field:
        raise FieldNotFoundException()
    old_values = get_model_snapshot(field)
    await delete_form_field_query(db, field)
    await create_audit_log(
        db,
        AuditLog(
            company_id=current_user.company_id,
            user_id=current_user.id,
            action=JOB_FORM_FIELD_DELETE,
            entity_type=JOB_FORM_FIELD,
            entity_id=field_id,
            old_values=old_values,
        ),
    )
    await db.commit()
    return FormFieldDeletedResponse(deleted=True)


async def reorder_fields(
    db: AsyncSession,
    *,
    job_id: int,
    data: ReorderFieldsRequest,
    current_user: User,
) -> ReorderFieldsResponse:
    reorder_payload = [
        {"field_id": item.field_id, "order_index": item.order_index}
        for item in data.order
    ]
    for item in data.order:
        await update_field_order(db, job_id=job_id, field_id=item.field_id, order_index=item.order_index)
    await create_audit_log(
        db,
        AuditLog(
            company_id=current_user.company_id,
            user_id=current_user.id,
            action=JOB_FORM_FIELD_REORDER,
            entity_type=JOB_FORM_FIELD,
            entity_id=job_id,
            new_values={"job_id": job_id, "order": reorder_payload},
        ),
    )
    await db.commit()
    return ReorderFieldsResponse(reordered=True)
