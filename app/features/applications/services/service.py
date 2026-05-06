"""Application business logic."""

import json

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    ApplicationNotFoundException,
    JobNotFoundException,
    MissingDocumentsException,
)
from app.core.utils.pagination import PaginationParams
from app.core.utils.ticket import generate_ticket_code
from app.features.applications.models import (
    Application,
    ApplicationAnswer,
    ApplicationDocument,
    ApplicationStatusLog,
)
from app.features.applications.repositories.repository import (
    add_answer,
    add_document,
    add_status_log,
    get_application_for_company,
    get_company_by_id,
    get_form_field_by_key,
    get_form_fields_by_job_id,
    get_published_job_by_id,
    get_user_by_email,
    list_applications as list_applications_query,
    list_public_jobs as list_public_jobs_query,
    save_application,
    save_ticket,
    save_user,
    update_application_status as update_application_status_repo,
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
from app.features.applications.services.mapper import map_job_to_public_item
from app.features.applications.services.validator import (
    validate_public_apply_requirements,
)
from app.features.tickets.models import Ticket
from app.features.users.models import User
from app.shared.constants.storage import ALLOWED_EXTENSIONS, MAX_FILE_SIZE_MB
from app.shared.enums.application_status import ApplicationStatus
from app.shared.enums.document_type import DocumentType
from app.shared.enums.ticket_status import TicketStatus
from app.shared.enums.user_roles import UserRole
from app.shared.helpers.storage import (
    generate_filename,
    upload_file,
)
from app.shared.schemas.response import PaginatedResponse


async def list_public_jobs(
    db: AsyncSession,
    *,
    pagination: PaginationParams,
    q: str | None = None,
    location: str | None = None,
) -> PaginatedResponse[PublicJobItem]:
    jobs, total = await list_public_jobs_query(
        db, pagination=pagination, q=q, location=location
    )
    items = []
    for job in jobs:
        company = await get_company_by_id(db, job.company_id)
        items.append(map_job_to_public_item(job, company))
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


async def get_public_job_detail(
    db: AsyncSession, job_id: int
) -> PublicJobDetailResponse:
    job = await get_published_job_by_id(db, job_id)
    if not job:
        raise JobNotFoundException()
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


async def public_apply(
    db: AsyncSession,
    *,
    data: PublicApplyCommand,
    documents: list[UploadFile] | None = None,
) -> PublicApplyResponse:
    # Validate all requirements
    await validate_public_apply_requirements(db, data, documents)

    # Get job and applicant
    job = await get_published_job_by_id(db, data.job_id)
    applicant = await get_user_by_email(db, data.email)
    if not applicant:
        applicant = await save_user(
            db,
            User(
                email=data.email,
                full_name=data.full_name,
                phone=data.phone,
                role=UserRole.APPLICANT,
            ),
        )

    application = await save_application(
        db,
        Application(
            job_id=data.job_id,
            applicant_id=applicant.id,
            status=ApplicationStatus.APPLIED,
        ),
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
            subject=f"Application for {job.title if job else 'Unknown Position'}",
        ),
    )
    await add_status_log(
        db,
        ApplicationStatusLog(
            application_id=application.id, to_status=ApplicationStatus.APPLIED.value
        ),
    )
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
    ext = (upload.filename or "").split(".")[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        if skip_invalid:
            return
        raise InvalidFileTypeException()
    content = await upload.read()
    if len(content) > MAX_FILE_SIZE_MB * 1024 * 1024:
        if skip_invalid:
            return
        raise FileTooLargeException()
    prefix = "portfolios" if document_type == DocumentType.PORTFOLIO else "documents"
    key = generate_filename(upload.filename or "unknown", prefix)
    file_url = upload_file(
        content=content,
        key=key,
        content_type=upload.content_type or "application/pdf",
    )
    await add_document(
        db,
        ApplicationDocument(
            application_id=application_id,
            document_type=document_type,
            file_name=upload.filename,
            file_url=file_url,
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
    
    items = []
    for app in applications:
        # Pydantic model_validate handles attribute access, but status needs .value
        item_data = {
            "id": app.id,
            "job_id": app.job_id,
            "applicant_id": app.applicant_id,
            "status": app.status.value,
            "created_at": app.created_at.isoformat() if app.created_at else None
        }
        items.append(ApplicationListItem.model_validate(item_data))

    return PaginatedResponse(
        data=items,
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
        raise ApplicationNotFoundException()
    old_status = application.status
    await update_application_status_repo(db, application, new_status)
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
