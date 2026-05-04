"""Application business logic."""
import json

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.utils.pagination import PaginationParams
from app.core.utils.ticket import generate_ticket_code
from app.features.applications.repositories.repository import (
    add_answer,
    add_document,
    add_status_log,
    get_application_by_job_and_applicant,
    get_application_for_company,
    get_company_by_id,
    get_form_field_by_key,
    get_form_fields_by_job_id,
    get_published_job_by_id,
    get_public_job_by_id,
    get_user_by_email,
    list_applications as list_applications_query,
    list_public_jobs as list_public_jobs_query,
    save_application,
    save_ticket,
    save_user,
)
from app.features.applications.schemas.schema import (
    ApplicationListItem,
    ApplicationStatusUpdateResponse,
    PublicApplyCommand,
    PublicApplyResponse,
    PublicJobDetailResponse,
    PublicJobFormField,
    PublicJobItem,
)
from app.features.models import (
    Application,
    ApplicationAnswer,
    ApplicationDocument,
    ApplicationStatusLog,
    Ticket,
    User,
)
from app.shared.constants.errors import ERR_DUPLICATE_APPLICATION
from app.shared.constants.storage import ALLOWED_EXTENSIONS, MAX_FILE_SIZE_MB
from app.shared.enums.application_status import ApplicationStatus
from app.shared.enums.document_type import DocumentType
from app.shared.enums.ticket_status import TicketStatus
from app.shared.enums.user_roles import UserRole
from app.shared.helpers.storage import build_public_url, generate_filename, get_s3_client
from app.shared.schemas.response import PaginatedResponse


async def list_public_jobs(
    db: AsyncSession,
    *,
    pagination: PaginationParams,
    q: str | None = None,
    location: str | None = None,
) -> PaginatedResponse[PublicJobItem]:
    jobs, total = await list_public_jobs_query(db, pagination=pagination, q=q, location=location)
    items = []
    for job in jobs:
        company = await get_company_by_id(db, job.company_id)
        items.append(
            PublicJobItem(
                id=job.id,
                title=job.title,
                department=job.department,
                employment_type=job.employment_type.value,
                location=job.location,
                salary_min=job.salary_min,
                salary_max=job.salary_max,
                description=job.description,
                apply_code=job.apply_code,
                company_name=company.name if company else None,
                published_at=job.published_at.isoformat() if job.published_at else None,
            )
        )
    pages = (total + pagination.per_page - 1) // pagination.per_page
    return PaginatedResponse(
        data=items,
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
        total_pages=pages,
        has_next=pagination.page < pages,
        has_prev=pagination.page > 1,
    )


async def get_public_job_detail(db: AsyncSession, job_id: int) -> PublicJobDetailResponse:
    job = await get_public_job_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    company = await get_company_by_id(db, job.company_id)
    form_fields = await get_form_fields_by_job_id(db, job_id)
    return PublicJobDetailResponse(
        id=job.id,
        title=job.title,
        description=job.description,
        responsibilities=job.responsibilities,
        benefits=job.benefits,
        employment_type=job.employment_type.value,
        location=job.location,
        company_name=company.name if company else None,
        form_fields=[
            PublicJobFormField(
                field_key=field.field_key,
                field_type=field.field_type.value,
                label=field.label,
                is_required=field.is_required,
            )
            for field in form_fields
        ],
    )


from app.features.applications.repositories.repository import get_knockout_rules_by_job_id

async def public_apply(
    db: AsyncSession,
    *,
    data: PublicApplyCommand,
    documents: list[UploadFile] | None = None,
) -> PublicApplyResponse:
    job = await get_published_job_by_id(db, data.job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found or not published")

    # VALIDATION 1: Mandatory Form Fields
    form_fields = await get_form_fields_by_job_id(db, job_id=data.job_id)
    answers = json.loads(data.answers_json) if data.answers_json else {}
    for field in form_fields:
        if field.is_required and not answers.get(field.field_key):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Field '{field.label}' is required")

    # VALIDATION 2: Required Documents
    knockout_rules = await get_knockout_rules_by_job_id(db, job_id=data.job_id)
    required_docs = [r.target_value.lower() for r in knockout_rules if r.rule_type == "document" and r.is_active]
    
    uploaded_filenames = [upload.filename.lower() for upload in documents] if documents else []
    for req_doc in required_docs:
        found = any(req_doc in fname for fname in uploaded_filenames)
        if not found:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Required document '{req_doc}' is missing")

    applicant = await get_user_by_email(db, data.email)
    if applicant:
        duplicate = await get_application_by_job_and_applicant(
            db,
            job_id=data.job_id,
            applicant_id=applicant.id,
        )
        if duplicate and not job.allow_multiple_apply:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=ERR_DUPLICATE_APPLICATION)
    else:
        applicant = await save_user(
            db,
            User(email=data.email, full_name=data.full_name, phone=data.phone, role=UserRole.APPLICANT),
        )

    application = await save_application(
        db,
        Application(job_id=data.job_id, applicant_id=applicant.id, status=ApplicationStatus.APPLIED),
    )

    if data.answers_json:
        answers = json.loads(data.answers_json)
        for key, value in answers.items():
            field = await get_form_field_by_key(db, job_id=data.job_id, field_key=key)
            if field:
                await add_answer(
                    db,
                    ApplicationAnswer(
                        application_id=application.id,
                        form_field_id=field.id,
                        value_text=str(value) if value is not None else None,
                    ),
                )


    for upload in documents or []:
        try:
            await _store_uploaded_document(
                db,
                application_id=application.id,
                upload=upload,
                document_type=DocumentType.LAINNYA,
                skip_invalid=True,
            )
        except HTTPException:
            continue

    ticket = await save_ticket(
        db,
        Ticket(
            application_id=application.id,
            code=generate_ticket_code(),
            status=TicketStatus.OPEN,
            subject=f"Application for {job.title}",
        ),
    )
    await add_status_log(db, ApplicationStatusLog(application_id=application.id, to_status=ApplicationStatus.APPLIED.value))
    await db.commit()
    await db.refresh(ticket)
    return PublicApplyResponse(
        application_id=application.id,
        ticket_code=ticket.code,
        status=ApplicationStatus.APPLIED.value,
    )


async def _store_uploaded_document(
    db: AsyncSession,
    *,
    application_id: int,
    upload: UploadFile,
    document_type: DocumentType,
    skip_invalid: bool = False,
) -> None:
    ext = upload.filename.split(".")[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        if skip_invalid:
            return
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file type")
    content = await upload.read()
    if len(content) > MAX_FILE_SIZE_MB * 1024 * 1024:
        if skip_invalid:
            return
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File too large")
    prefix = "portfolios" if document_type == DocumentType.PORTFOLIO else "documents"
    key = generate_filename(upload.filename, prefix)
    s3 = get_s3_client()
    s3.put_object(
        Bucket=settings.R2_BUCKET_NAME,
        Key=key,
        Body=content,
        ContentType=upload.content_type or "application/pdf",
    )
    await add_document(
        db,
        ApplicationDocument(
            application_id=application_id,
            document_type=document_type,
            file_name=upload.filename,
            file_url=build_public_url(key),
            file_size=len(content),
            mime_type=upload.content_type or "application/pdf",
        ),
    )


async def list_applications(
    db: AsyncSession,
    *,
    current_user: User,
    pagination: PaginationParams,
    job_id: int | None = None,
    status_filter: ApplicationStatus | None = None,
    q: str | None = None,
) -> PaginatedResponse[ApplicationListItem]:
    applications, total = await list_applications_query(
        db,
        company_id=current_user.company_id,
        pagination=pagination,
        job_id=job_id,
        status=status_filter,
        q=q,
    )
    pages = (total + pagination.per_page - 1) // pagination.per_page
    return PaginatedResponse(
        data=[
            ApplicationListItem(
                id=item.id,
                job_id=item.job_id,
                applicant_id=item.applicant_id,
                status=item.status.value,
                created_at=item.created_at.isoformat() if item.created_at else None,
            )
            for item in applications
        ],
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
        total_pages=pages,
        has_next=pagination.page < pages,
        has_prev=pagination.page > 1,
    )


async def update_application_status(
    db: AsyncSession,
    *,
    current_user: User,
    application_id: int,
    new_status: ApplicationStatus,
    reason: str | None = None,
) -> ApplicationStatusUpdateResponse:
    application = await get_application_for_company(
        db,
        application_id=application_id,
        company_id=current_user.company_id,
    )
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    old_status = application.status
    application.status = new_status
    await add_status_log(
        db,
        ApplicationStatusLog(
            application_id=application.id,
            from_status=old_status.value if old_status else None,
            to_status=new_status.value,
            changed_by=current_user.id,
            reason=reason,
        ),
    )
    await db.commit()
    return ApplicationStatusUpdateResponse(
        application_id=application.id,
        old_status=old_status.value if old_status else None,
        new_status=new_status.value,
    )
