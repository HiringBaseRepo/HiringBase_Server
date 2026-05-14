"""HR Custom Form Builder API."""
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.base import get_db
from app.features.auth.dependencies.auth import require_hr
from app.features.job_forms.schemas.schema import (
    CreateFormFieldRequest,
    FormFieldCreatedResponse,
    FormFieldDeletedResponse,
    FormFieldUpdatedResponse,
    ReorderFieldsRequest,
    ReorderFieldsResponse,
)
from app.features.job_forms.services.service import (
    create_form_field as create_form_field_service,
    delete_form_field as delete_form_field_service,
    reorder_fields as reorder_fields_service,
    update_form_field as update_form_field_service,
)
from app.shared.schemas.response import StandardResponse
from app.shared.enums.field_type import FormFieldType

router = APIRouter(prefix="/job-forms", tags=["Job Form Builder"])


@router.post("/{job_id}/fields", response_model=StandardResponse[FormFieldCreatedResponse])
async def create_form_field(
    job_id: int,
    field_key: str,
    field_type: FormFieldType,
    label: str,
    placeholder: Optional[str] = None,
    help_text: Optional[str] = None,
    options: Optional[dict] = None,
    is_required: bool = True,
    order_index: int = 0,
    validation_rules: Optional[dict] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_hr),
):
    data = CreateFormFieldRequest(
        field_key=field_key,
        field_type=field_type,
        label=label,
        placeholder=placeholder,
        help_text=help_text,
        options=options,
        is_required=is_required,
        order_index=order_index,
        validation_rules=validation_rules,
    )
    result = await create_form_field_service(
        db,
        job_id=job_id,
        data=data,
        current_user=current_user,
    )
    return StandardResponse.ok(data=result)


@router.patch("/{job_id}/fields/{field_id}", response_model=StandardResponse[FormFieldUpdatedResponse])
async def update_form_field(
    job_id: int,
    field_id: int,
    updates: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_hr),
):
    result = await update_form_field_service(
        db,
        job_id=job_id,
        field_id=field_id,
        updates=updates,
        current_user=current_user,
    )
    return StandardResponse.ok(data=result)


@router.delete("/{job_id}/fields/{field_id}", response_model=StandardResponse[FormFieldDeletedResponse])
async def delete_form_field(
    job_id: int,
    field_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_hr),
):
    result = await delete_form_field_service(
        db,
        job_id=job_id,
        field_id=field_id,
        current_user=current_user,
    )
    return StandardResponse.ok(data=result)


@router.post("/{job_id}/fields/reorder", response_model=StandardResponse[ReorderFieldsResponse])
async def reorder_fields(
    job_id: int,
    data: ReorderFieldsRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_hr),
):
    result = await reorder_fields_service(
        db,
        job_id=job_id,
        data=data,
        current_user=current_user,
    )
    return StandardResponse.ok(data=result)
