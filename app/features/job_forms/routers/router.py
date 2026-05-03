"""HR Custom Form Builder API."""
from typing import Optional, List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.core.database.base import get_db
from app.features.auth.dependencies.auth import require_hr
from app.features.models import JobFormField, Job
from app.shared.schemas.response import StandardResponse
from app.shared.enums.field_type import FormFieldType

router = APIRouter(prefix="/job-forms", tags=["Job Form Builder"])


@router.post("/{job_id}/fields", response_model=StandardResponse[dict])
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
    field = JobFormField(
        job_id=job_id,
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
    db.add(field)
    await db.commit()
    await db.refresh(field)
    return StandardResponse.ok(data={"field_id": field.id, "field_key": field.field_key})


@router.patch("/{job_id}/fields/{field_id}", response_model=StandardResponse[dict])
async def update_form_field(
    job_id: int,
    field_id: int,
    updates: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_hr),
):
    result = await db.execute(select(JobFormField).where(JobFormField.id == field_id, JobFormField.job_id == job_id))
    field = result.scalar_one_or_none()
    if not field:
        return StandardResponse.error(message="Field not found", status_code=404)
    for key, value in updates.items():
        if hasattr(field, key):
            setattr(field, key, value)
    await db.commit()
    return StandardResponse.ok(data={"field_id": field.id, "updated": True})


@router.delete("/{job_id}/fields/{field_id}", response_model=StandardResponse[dict])
async def delete_form_field(
    job_id: int,
    field_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_hr),
):
    result = await db.execute(select(JobFormField).where(JobFormField.id == field_id, JobFormField.job_id == job_id))
    field = result.scalar_one_or_none()
    if not field:
        return StandardResponse.error(message="Field not found", status_code=404)
    await db.delete(field)
    await db.commit()
    return StandardResponse.ok(data={"deleted": True})


@router.post("/{job_id}/fields/reorder", response_model=StandardResponse[dict])
async def reorder_fields(
    job_id: int,
    order: List[dict],  # [{"field_id": 1, "order_index": 0}, ...]
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_hr),
):
    for item in order:
        await db.execute(
            update(JobFormField)
            .where(JobFormField.id == item["field_id"], JobFormField.job_id == job_id)
            .values(order_index=item["order_index"])
        )
    await db.commit()
    return StandardResponse.ok(data={"reordered": True})
