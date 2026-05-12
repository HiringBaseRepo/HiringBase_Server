"""Job management business logic."""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import JobNotFoundException
from app.core.utils.pagination import PaginationParams
from app.core.utils.ticket import generate_apply_code
from app.features.jobs.models import Job, JobFormField, JobRequirement
from app.features.jobs.repositories.repository import (
    get_form_fields_by_job_id,
    get_job_for_company,
    get_knockout_rules_by_job_id,
    get_requirements_by_job_id,
    save_form_fields,
    save_job,
    save_requirements,
)
from app.features.audit_logs.models import AuditLog
from app.features.audit_logs.repositories.repository import create_audit_log
from app.features.jobs.repositories.repository import (
    list_jobs as list_jobs_query,
)
from app.features.jobs.schemas.schema import (
    AddJobRequirementsRequest,
    CreateJobStep1Request,
    JobCloseResponse,
    JobDetailResponse,
    JobFormFieldInput,
    JobListItem,
    JobPublishResponse,
    JobStepResponse,
    PublishJobRequest,
    SetupJobFormRequest,
)
from app.features.jobs.services.mapper import (
    map_form_field_to_item,
    map_job_to_list_item,
    map_knockout_rule_to_item,
    map_requirement_to_item,
)
from app.features.users.models import User
from app.shared.enums.job_status import JobStatus
from app.shared.helpers.localization import get_label
from app.shared.schemas.response import PaginatedResponse

async def create_job_step1(
    db: AsyncSession,
    *,
    current_user: User,
    data: CreateJobStep1Request,
) -> JobStepResponse:
    job = Job(
        company_id=current_user.company_id,
        created_by=current_user.id,
        title=data.title,
        department=data.department,
        employment_type=data.employment_type,
        location=data.location,
        salary_min=data.salary_min,
        salary_max=data.salary_max,
        description=data.description,
        responsibilities=data.responsibilities,
        benefits=data.benefits,
        status=JobStatus.DRAFT,
    )
    job = await save_job(db, job)
    await create_audit_log(
        db,
        AuditLog(
            company_id=current_user.company_id,
            user_id=current_user.id,
            action="JOB_CREATE",
            entity_type="job",
            entity_id=job.id,
            new_values={"title": job.title, "status": job.status},
        ),
    )
    await db.commit()
    return JobStepResponse(
        job_id=job.id, status=job.status, status_label=get_label(job.status)
    )


async def add_job_requirements(
    db: AsyncSession,
    *,
    current_user: User,
    job_id: int,
    data: AddJobRequirementsRequest,
) -> JobStepResponse:
    job = await get_job_for_company(db, job_id, current_user.company_id)
    if not job:
        raise JobNotFoundException()

    requirements = [
        JobRequirement(
            job_id=job_id,
            category=item.category,
            name=item.name,
            value=item.value,
            is_required=item.is_required,
            priority=item.priority,
        )
        for item in data.requirements
    ]
    await save_requirements(db, requirements)
    
    # Audit Log
    await create_audit_log(
        db,
        AuditLog(
            company_id=current_user.company_id,
            user_id=current_user.id,
            action="JOB_REQUIREMENTS_UPDATE",
            entity_type="job",
            entity_id=job_id,
            new_values={"count": len(requirements)}
        )
    )
    
    await db.commit()
    return JobStepResponse(job_id=job_id, requirements_added=len(requirements))


async def setup_job_form(
    db: AsyncSession,
    *,
    current_user: User,
    job_id: int,
    data: SetupJobFormRequest,
) -> JobStepResponse:
    job = await get_job_for_company(db, job_id, current_user.company_id)
    if not job:
        raise JobNotFoundException()

    fields = [_build_form_field(job_id, item) for item in data.fields]
    await save_form_fields(db, fields)
    
    # Audit Log
    await create_audit_log(
        db,
        AuditLog(
            company_id=current_user.company_id,
            user_id=current_user.id,
            action="JOB_FORM_UPDATE",
            entity_type="job",
            entity_id=job_id,
            new_values={"count": len(fields)}
        )
    )
    
    await db.commit()
    return JobStepResponse(job_id=job_id, form_fields_added=len(fields))


def _build_form_field(job_id: int, item: JobFormFieldInput) -> JobFormField:
    return JobFormField(
        job_id=job_id,
        field_key=item.field_key,
        field_type=item.field_type,
        label=item.label,
        placeholder=item.placeholder,
        help_text=item.help_text,
        options=item.options,
        is_required=item.is_required,
        order_index=item.order_index,
        validation_rules=item.validation_rules,
    )


async def publish_job(
    db: AsyncSession,
    *,
    current_user: User,
    job_id: int,
    data: PublishJobRequest,
) -> JobPublishResponse:
    job = await get_job_for_company(db, job_id, current_user.company_id)
    if not job:
        raise JobNotFoundException()

    job.apply_code = generate_apply_code()
    if data.mode == "public":
        job.status = JobStatus.PUBLISHED
        job.is_public = True
        job.published_at = datetime.utcnow()
    elif data.mode == "private":
        job.status = JobStatus.PRIVATE
        job.is_public = False
    elif data.mode == "scheduled" and data.scheduled_at:
        job.status = JobStatus.SCHEDULED
        job.scheduled_publish_at = data.scheduled_at

    await create_audit_log(
        db,
        AuditLog(
            company_id=current_user.company_id,
            user_id=current_user.id,
            action="JOB_PUBLISH",
            entity_type="job",
            entity_id=job.id,
            new_values={"status": job.status, "mode": data.mode},
        ),
    )
    await db.commit()
    response = JobPublishResponse(
        job_id=job.id,
        status=job.status,
        status_label=get_label(job.status),
        apply_code=job.apply_code,
        is_public=job.is_public,
    )
    return response


async def list_jobs(
    db: AsyncSession,
    *,
    current_user: User,
    pagination: PaginationParams,
    status: JobStatus | None = None,
    q: str | None = None,
) -> PaginatedResponse[JobListItem]:
    jobs, total = await list_jobs_query(
        db,
        company_id=current_user.company_id,
        pagination=pagination,
        status=status,
        q=q,
    )
    pages = (total + pagination.per_page - 1) // pagination.per_page
    return PaginatedResponse(
        data=[map_job_to_list_item(job) for job in jobs],
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
        total_pages=pages,
        has_next=pagination.page < pages,
        has_prev=pagination.page > 1,
    )


async def get_job_detail(
    db: AsyncSession,
    *,
    current_user: User,
    job_id: int,
) -> JobDetailResponse:
    job = await get_job_for_company(db, job_id, current_user.company_id)
    if not job:
        raise JobNotFoundException()

    requirements = await get_requirements_by_job_id(db, job_id)
    form_fields = await get_form_fields_by_job_id(db, job_id)
    knockout_rules = await get_knockout_rules_by_job_id(db, job_id)
    return JobDetailResponse(
        id=job.id,
        title=job.title,
        description=job.description,
        requirements=[map_requirement_to_item(item) for item in requirements],
        form_fields=[map_form_field_to_item(item) for item in form_fields],
        knockout_rules=[map_knockout_rule_to_item(item) for item in knockout_rules],
    )


async def close_job(
    db: AsyncSession,
    *,
    current_user: User,
    job_id: int,
) -> JobCloseResponse:
    job = await get_job_for_company(db, job_id, current_user.company_id)
    if not job:
        raise JobNotFoundException()

    job.status = JobStatus.CLOSED
    job.closed_at = datetime.utcnow()
    await create_audit_log(
        db,
        AuditLog(
            company_id=current_user.company_id,
            user_id=current_user.id,
            action="JOB_CLOSE",
            entity_type="job",
            entity_id=job.id,
            new_values={"status": job.status},
        ),
    )
    await db.commit()
    response = JobCloseResponse(
        job_id=job.id, status=job.status, status_label=get_label(job.status)
    )
    return response
