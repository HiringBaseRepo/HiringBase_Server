"""Application business logic."""

import json

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.features.audit_logs.models import AuditLog
from app.features.audit_logs.repositories.repository import create_audit_log
from app.core.exceptions import (
    ApplicationNotFoundException,
    FileTooLargeException,
    InvalidFileTypeException,
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
    get_application_detail as get_application_detail_repo,
)
from app.features.applications.schemas.schema import (
    PublicJobFormField,
    PublicJobItem,
    PublicJobDetailResponse,
    ApplicationListItem,
    ApplicationStatusUpdateResponse,
    PublicApplyCommand,
    PublicApplyResponse,
    ApplicationDetailResponse,
    ApplicationAnswerResponse,
    ApplicationDocumentResponse,
    CandidateScoreResponse,
)
from app.shared.helpers.localization import get_label
from app.features.applications.services.mapper import map_job_to_public_item
from app.features.applications.services.validator import (
    validate_public_apply_requirements,
)
from app.features.tickets.models import Ticket
from app.features.users.models import User
from app.shared.constants.storage import ALLOWED_EXTENSIONS, MAX_FILE_SIZE_MB, UPLOAD_PREFIX_PORTFOLIO, UPLOAD_PREFIX_DOCUMENT
from app.shared.enums.application_status import ApplicationStatus
from app.shared.enums.document_type import DocumentType
from app.shared.enums.ticket_status import TicketStatus
from app.shared.enums.user_roles import UserRole
from app.shared.helpers.storage import (
    generate_filename,
    upload_file,
)
from app.shared.schemas.response import PaginatedResponse
from app.shared.tasks.mail_tasks import send_ticket_email



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
        
        # Save as metadata in application.notes for safety
        application.notes = data.answers_json
        
        for key, value in answers.items():
            field = await get_form_field_by_key(db, job_id=data.job_id, field_key=key)
            if field:
                print(f"DEBUG SUBMIT: Field found for key '{key}' (ID: {field.id}). Saving value: {value}")
                await add_answer(
                    db,
                    ApplicationAnswer(
                        application_id=application.id,
                        form_field_id=field.id,
                        value_text=str(value) if value is not None else None,
                    ),
                )
     

    for upload in documents or []:
        # Detect document type from filename
        fname = (upload.filename or "").lower()
        doc_type = DocumentType.OTHERS
        if any(k in fname for k in ["ktp", "identity", "id_card", "identitas"]):
            doc_type = DocumentType.IDENTITY_CARD
        elif any(k in fname for k in ["skck", "criminal", "record", "polisi"]):
            doc_type = DocumentType.CRIMINAL_RECORD
        elif any(k in fname for k in ["ijazah", "degree", "diploma", "certificate"]):
            doc_type = DocumentType.DEGREE
        
        try:
            await _store_uploaded_document(
                db,
                application_id=application.id,
                upload=upload,
                document_type=doc_type,
                skip_invalid=True,
            )
        except (InvalidFileTypeException, FileTooLargeException):
            continue

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

    await db.commit()


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
    prefix = UPLOAD_PREFIX_PORTFOLIO if document_type == DocumentType.PORTFOLIO else UPLOAD_PREFIX_DOCUMENT
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
            "status_label": get_label(app.status),
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
    from app.core.utils.audit import get_model_snapshot
    old_values = get_model_snapshot(application)
    
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
    await create_audit_log(
        db,
        AuditLog(
            company_id=current_user.company_id,
            user_id=current_user.id,
            action="APPLICATION_STATUS_UPDATE",
            entity_type="application",
            entity_id=application.id,
            old_values=old_values,
            new_values={"status": new_status.value, "reason": reason},
        ),
    )
    await db.commit()
    return ApplicationStatusUpdateResponse(
        application_id=application.id,
        old_status=old_status.value if old_status else None,
        new_status=new_status.value,
        new_status_label=get_label(new_status),
    )


async def get_application_detail(
    db: AsyncSession,
    *,
    current_user: User,
    application_id: int,
) -> ApplicationDetailResponse:
    application = await get_application_detail_repo(
        db, application_id=application_id, company_id=current_user.company_id
    )
    if not application:
        raise ApplicationNotFoundException()

    # Debugging
    print(f"DEBUG: Application ID {application.id} has {len(application.answers)} answers and {len(application.documents)} documents")
    
    answers = []
    for ans in application.answers:
        print(f"DEBUG: Mapping answer {ans.id} for field {ans.form_field.field_key if ans.form_field else 'UNKNOWN'}")
        answers.append(
            ApplicationAnswerResponse(
                field_key=ans.form_field.field_key if ans.form_field else "unknown",
                label=ans.form_field.label if ans.form_field else "Unknown Field",
                value=ans.value_text or ans.value_number or ans.value_json,
            )
        )
    
    # Fallback to notes if no formal answers found
    if not answers and application.notes:
        try:
            import json
            notes_data = json.loads(application.notes)
            for key, value in notes_data.items():
                answers.append(
                    ApplicationAnswerResponse(
                        field_key=key,
                        label=key.replace("_", " ").title(),
                        value=value,
                    )
                )
            print(f"DEBUG: Loaded {len(answers)} answers from fallback metadata (notes)")
        except:
            pass

    documents = []
    for doc in application.documents:
        print(f"DEBUG: Mapping document {doc.id}")
        documents.append(
            ApplicationDocumentResponse(
                id=doc.id,
                document_type=doc.document_type.value,
                file_name=doc.file_name,
                file_url=doc.file_url,
            )
        )

    score = None
    if application.scores:
        # scores is a list due to relationship, get the first one
        s = application.scores[0] if isinstance(application.scores, list) else application.scores
        score = CandidateScoreResponse(
            skill_match_score=s.skill_match_score,
            experience_score=s.experience_score,
            education_score=s.education_score,
            portfolio_score=s.portfolio_score,
            soft_skill_score=s.soft_skill_score,
            administrative_score=s.administrative_score,
            final_score=s.final_score,
            explanation=s.explanation,
            red_flags=s.red_flags,
            risk_level=s.risk_level,
        )

    return ApplicationDetailResponse(
        id=application.id,
        job_id=application.job_id,
        job_title=application.job.title,
        applicant_name=application.applicant.full_name,
        applicant_email=application.applicant.email,
        status=application.status.value,
        status_label=get_label(application.status),
        created_at=application.created_at,
        answers=answers,
        documents=documents,
        score=score,
    )
