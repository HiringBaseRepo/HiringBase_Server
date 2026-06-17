"""Public application service."""

import json
import structlog

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.audit_logs.models import AuditLog
from app.features.audit_logs.repositories.repository import create_audit_log
from app.core.exceptions import (
    FileTooLargeException,
    InvalidFileTypeException,
    JobNotFoundException,
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
    get_company_by_id,
    get_form_field_by_key,
    get_form_fields_by_job_id,
    get_published_job_by_id,
    get_user_by_email,
    list_public_jobs as list_public_jobs_query,
    save_application,
    save_ticket,
    save_user,
)
from app.features.applications.schemas.schema import (
    PublicJobFormField,
    PublicJobItem,
    PublicJobDetailResponse,
    PublicApplyCommand,
    PublicApplyResponse,
)
from app.shared.helpers.localization import get_label
from app.features.applications.services.mapper import map_job_to_public_item
from app.features.applications.services.validator import (
    validate_public_apply_requirements,
)
from app.features.notifications.services.service import create_notification_for_internal_audience
from app.features.tickets.models import Ticket
from app.features.users.models import User
from app.shared.constants.storage import ALLOWED_EXTENSIONS, MAX_FILE_SIZE_MB, UPLOAD_PREFIX_PORTFOLIO, UPLOAD_PREFIX_DOCUMENT
from app.shared.constants.audit_actions import APPLICATION_SUBMIT
from app.shared.constants.audit_entities import APPLICATION
from app.shared.enums.application_status import ApplicationStatus
from app.shared.enums.document_type import DocumentType
from app.shared.enums.notification_type import NotificationType
from app.shared.enums.ticket_status import TicketStatus
from app.shared.enums.user_roles import UserRole
from app.shared.helpers.storage import (
    delete_file_async,
    generate_filename,
    upload_file_async,
)
from app.shared.schemas.response import PaginatedResponse
from app.shared.tasks.mail_tasks import send_ticket_email

logger = structlog.get_logger(__name__)


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
        employment_type_label=get_label(job.employment_type),
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
    documents_data: list[dict] | None = None,
) -> PublicApplyResponse:
    # Validate all requirements
    await validate_public_apply_requirements(db, data, documents_data)

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
    else:
        if data.full_name and applicant.full_name != data.full_name:
            applicant.full_name = data.full_name
        if data.phone and applicant.phone != data.phone:
            applicant.phone = data.phone

    application = await save_application(
        db,
        Application(
            job_id=data.job_id,
            applicant_id=applicant.id,
            status=ApplicationStatus.APPLIED,
        ),
    )

    uploaded_keys: list[str] = []
    if data.answers_json:
        application.notes = data.answers_json

    answers = json.loads(data.answers_json) if data.answers_json else {}
    form_fields = await get_form_fields_by_job_id(db, job_id=data.job_id)
    for field in form_fields:
        val = None
        if field.field_key == "full_name":
            val = data.full_name
        elif field.field_key in ("email", "email_address"):
            val = data.email
        elif field.field_key in ("phone", "phone_number", "whatsapp"):
            val = data.phone
        elif field.field_key in ("work_experience", "experience"):
            val = answers.get("experience") or answers.get("work_experience")
        elif field.field_key in ("ijazah", "ijazah_terakhir"):
            doc = next((d for d in (documents_data or []) if d["type"].value == "degree"), None)
            val = doc["file"].filename if doc else None
        elif field.field_key == "ktp":
            doc = next((d for d in (documents_data or []) if d["type"].value == "identity_card"), None)
            val = doc["file"].filename if doc else None
        elif field.field_key == "skck":
            doc = next((d for d in (documents_data or []) if d["type"].value == "criminal_record"), None)
            val = doc["file"].filename if doc else None
        elif field.field_key in ("surat_sehat", "surat_keterangan_sehat"):
            doc = next((d for d in (documents_data or []) if d["type"].value == "health_certificate"), None)
            val = doc["file"].filename if doc else None
        elif field.field_key in ("sertifikat", "sertifikat_keahlian"):
            doc = next((d for d in (documents_data or []) if d["type"].value == "certificate"), None)
            val = doc["file"].filename if doc else None
        elif field.field_key in ("cv", "portfolio", "portofolio"):
            doc = next((d for d in (documents_data or []) if d["type"].value == "portfolio"), None)
            val = doc["file"].filename if doc else None
        else:
            val = answers.get(field.field_key)

        if val is not None:
            await add_answer(
                db,
                ApplicationAnswer(
                    application_id=application.id,
                    form_field_id=field.id,
                    value_text=str(val),
                ),
            )
    for item in documents_data or []:
        upload = item["file"]
        doc_type = item["type"]
        uploaded_key = await _store_uploaded_document(
            db,
            application_id=application.id,
            upload=upload,
            document_type=doc_type,
            skip_invalid=False,
        )
        uploaded_keys.append(uploaded_key)

    ticket = await save_ticket(
        db,
        Ticket(
            application_id=application.id,
            code=generate_ticket_code(),
            status=TicketStatus.OPEN,
            subject=f"Lamaran untuk {job.title if job else 'Posisi Tidak Diketahui'}",
        ),
    )
    await add_status_log(
        db,
        ApplicationStatusLog(
            application_id=application.id, to_status=ApplicationStatus.APPLIED.value
        ),
    )
    await create_audit_log(
        db,
        AuditLog(
            company_id=job.company_id if job else None,
            user_id=applicant.id,
            action=APPLICATION_SUBMIT,
            entity_type=APPLICATION,
            entity_id=application.id,
            new_values={
                "job_id": data.job_id,
                "ticket_code": ticket.code,
                "status": ApplicationStatus.APPLIED.value,
                "answers_count": len(json.loads(data.answers_json)) if data.answers_json else 0,
                "documents_count": len(documents_data or []),
            },
        ),
    )
    await create_notification_for_internal_audience(
        db,
        actor_user_id=applicant.id,
        company_id=job.company_id if job else None,
        notification_type=NotificationType.NEW_APPLICATION,
        entity_type=APPLICATION,
        entity_id=application.id,
        message_params={
            "applicant_name": applicant.full_name,
            "job_title": job.title if job else "-",
            "ticket_code": ticket.code,
        },
    )

    try:
        await db.commit()
    except Exception:
        for key in uploaded_keys:
            try:
                await delete_file_async(key)
            except Exception as delete_exc:
                logger.warning(
                    "r2_rollback_delete_failed",
                    key=key,
                    error=str(delete_exc),
                )
        raise

    # Trigger Background Task: Send Ticket Email
    await send_ticket_email.kiq(
        email=applicant.email,
        name=applicant.full_name,
        ticket_number=ticket.code
    )

    return PublicApplyResponse(
        application_id=application.id,
        ticket_code=ticket.code,
        status=ApplicationStatus.APPLIED.value,
        status_label=get_label(ApplicationStatus.APPLIED),
    )


async def _store_uploaded_document(
    db: AsyncSession,
    *,
    application_id: int,
    upload: UploadFile,
    document_type: DocumentType,
    skip_invalid: bool = False,
) -> str:
    ext = (upload.filename or "").split(".")[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        if skip_invalid:
            return ""
        raise InvalidFileTypeException()
    content = await upload.read()
    if len(content) > MAX_FILE_SIZE_MB * 1024 * 1024:
        if skip_invalid:
            return ""
        raise FileTooLargeException()
    prefix = UPLOAD_PREFIX_PORTFOLIO if document_type == DocumentType.PORTFOLIO else UPLOAD_PREFIX_DOCUMENT
    key = generate_filename(upload.filename or "unknown", prefix)
    file_url = await upload_file_async(
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
    return key
