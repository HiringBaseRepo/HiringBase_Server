"""Vacancy Management API."""
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.core.database.base import get_db
from app.features.auth.dependencies import require_hr, get_current_user
from app.features.models import Job, JobRequirement, JobScoringTemplate, JobFormField, JobKnockoutRule, Application
from app.shared.schemas.response import StandardResponse, PaginatedResponse
from app.core.utils.pagination import PaginationParams
from app.shared.enums.job_status import JobStatus
from app.shared.enums.employment_type import EmploymentType
from app.shared.enums.field_type import FormFieldType
from app.core.utils.ticket import generate_apply_code
from app.shared.enums.user_roles import UserRole

router = APIRouter(prefix="/jobs", tags=["Jobs / Vacancies"])


@router.post("/create-step1", response_model=StandardResponse[dict])
async def create_job_step1(
    title: str,
    department: Optional[str] = None,
    employment_type: EmploymentType = EmploymentType.FULL_TIME,
    location: Optional[str] = None,
    salary_min: Optional[int] = None,
    salary_max: Optional[int] = None,
    description: str = "",
    responsibilities: Optional[str] = None,
    benefits: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_hr),
):
    job = Job(
        company_id=current_user.company_id,
        created_by=current_user.id,
        title=title,
        department=department,
        employment_type=employment_type,
        location=location,
        salary_min=salary_min,
        salary_max=salary_max,
        description=description,
        responsibilities=responsibilities,
        benefits=benefits,
        status=JobStatus.DRAFT,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return StandardResponse.ok(data={"job_id": job.id, "status": job.status.value}, message="Step 1 saved")


@router.post("/{job_id}/step2-requirements", response_model=StandardResponse[dict])
async def add_job_requirements(
    job_id: int,
    requirements: List[dict],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_hr),
):
    result = await db.execute(select(Job).where(Job.id == job_id, Job.company_id == current_user.company_id))
    job = result.scalar_one_or_none()
    if not job:
        return StandardResponse.error(message="Job not found", status_code=404)
    for req in requirements:
        r = JobRequirement(
            job_id=job_id,
            category=req.get("category"),
            name=req.get("name"),
            value=req.get("value"),
            is_required=req.get("is_required", True),
            priority=req.get("priority", 1),
        )
        db.add(r)
    await db.commit()
    return StandardResponse.ok(data={"job_id": job_id, "requirements_added": len(requirements)})


@router.post("/{job_id}/step3-form", response_model=StandardResponse[dict])
async def setup_job_form(
    job_id: int,
    fields: List[dict],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_hr),
):
    result = await db.execute(select(Job).where(Job.id == job_id, Job.company_id == current_user.company_id))
    job = result.scalar_one_or_none()
    if not job:
        return StandardResponse.error(message="Job not found", status_code=404)
    for f in fields:
        field = JobFormField(
            job_id=job_id,
            field_key=f.get("field_key"),
            field_type=FormFieldType(f.get("field_type")),
            label=f.get("label"),
            placeholder=f.get("placeholder"),
            help_text=f.get("help_text"),
            options=f.get("options"),
            is_required=f.get("is_required", True),
            order_index=f.get("order_index", 0),
            validation_rules=f.get("validation_rules"),
        )
        db.add(field)
    await db.commit()
    return StandardResponse.ok(data={"job_id": job_id, "form_fields_added": len(fields)})


@router.post("/{job_id}/step4-publish", response_model=StandardResponse[dict])
async def publish_job(
    job_id: int,
    mode: str = "public",  # public, private, scheduled
    scheduled_at: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_hr),
):
    result = await db.execute(select(Job).where(Job.id == job_id, Job.company_id == current_user.company_id))
    job = result.scalar_one_or_none()
    if not job:
        return StandardResponse.error(message="Job not found", status_code=404)

    job.apply_code = generate_apply_code()
    if mode == "public":
        job.status = JobStatus.PUBLISHED
        job.is_public = True
        job.published_at = datetime.utcnow()
    elif mode == "private":
        job.status = JobStatus.PRIVATE
        job.is_public = False
    elif mode == "scheduled" and scheduled_at:
        job.status = JobStatus.SCHEDULED
        job.scheduled_publish_at = scheduled_at

    await db.commit()
    await db.refresh(job)
    return StandardResponse.ok(data={
        "job_id": job.id,
        "status": job.status.value,
        "apply_code": job.apply_code,
        "is_public": job.is_public,
    })


@router.get("", response_model=StandardResponse[PaginatedResponse[dict]])
async def list_jobs(
    status: Optional[JobStatus] = None,
    q: Optional[str] = None,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_hr),
):
    stmt = select(Job).where(Job.company_id == current_user.company_id, Job.deleted_at.is_(None))
    if status:
        stmt = stmt.where(Job.status == status)
    if q:
        stmt = stmt.where(Job.title.ilike(f"%{q}%"))

    total_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_result.scalar_one()

    stmt = stmt.order_by(Job.created_at.desc()).offset(pagination.offset).limit(pagination.limit)
    result = await db.execute(stmt)
    items = []
    for j in result.scalars().all():
        items.append({
            "id": j.id, "title": j.title, "department": j.department,
            "employment_type": j.employment_type.value, "status": j.status.value,
            "location": j.location, "apply_code": j.apply_code,
            "published_at": j.published_at.isoformat() if j.published_at else None,
            "created_at": j.created_at.isoformat() if j.created_at else None,
        })

    pages = (total + pagination.per_page - 1) // pagination.per_page
    return StandardResponse.ok(data=PaginatedResponse(
        data=items, total=total, page=pagination.page,
        per_page=pagination.per_page, total_pages=pages,
        has_next=pagination.page < pages, has_prev=pagination.page > 1,
    ))


@router.get("/{job_id}", response_model=StandardResponse[dict])
async def get_job_detail(job_id: int, db: AsyncSession = Depends(get_db), current_user=Depends(require_hr)):
    result = await db.execute(select(Job).where(Job.id == job_id, Job.company_id == current_user.company_id))
    job = result.scalar_one_or_none()
    if not job:
        return StandardResponse.error(message="Job not found", status_code=404)

    reqs = await db.execute(select(JobRequirement).where(JobRequirement.job_id == job_id))
    form_fields = await db.execute(select(JobFormField).where(JobFormField.job_id == job_id).order_by(JobFormField.order_index))
    rules = await db.execute(select(JobKnockoutRule).where(JobKnockoutRule.job_id == job_id))

    return StandardResponse.ok(data={
        "id": job.id,
        "title": job.title,
        "description": job.description,
        "requirements": [{"id": r.id, "category": r.category, "name": r.name, "value": r.value, "is_required": r.is_required} for r in reqs.scalars().all()],
        "form_fields": [{"id": f.id, "field_key": f.field_key, "field_type": f.field_type.value, "label": f.label, "is_required": f.is_required} for f in form_fields.scalars().all()],
        "knockout_rules": [{"id": r.id, "rule_name": r.rule_name, "rule_type": r.rule_type, "action": r.action} for r in rules.scalars().all()],
    })


@router.patch("/{job_id}/close", response_model=StandardResponse[dict])
async def close_job(job_id: int, db: AsyncSession = Depends(get_db), current_user=Depends(require_hr)):
    result = await db.execute(select(Job).where(Job.id == job_id, Job.company_id == current_user.company_id))
    job = result.scalar_one_or_none()
    if not job:
        return StandardResponse.error(message="Job not found", status_code=404)
    job.status = JobStatus.CLOSED
    job.closed_at = datetime.utcnow()
    await db.commit()
    return StandardResponse.ok(data={"job_id": job.id, "status": job.status.value})
