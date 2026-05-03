"""Public Applicant + Application Management API."""
from typing import Optional, List
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime

from app.core.database.base import get_db
from app.features.auth.dependencies import get_current_user, require_hr, require_applicant
from app.features.models import (
    Application, Job, User, ApplicationAnswer, ApplicationDocument,
    ApplicationStatusLog, JobFormField, Ticket, CandidateScore, JobKnockoutRule,
    JobScoringTemplate, Company
)
from app.shared.schemas.response import StandardResponse, PaginatedResponse
from app.core.utils.pagination import PaginationParams
from app.core.utils.ticket import generate_ticket_code
from app.shared.enums.application_status import ApplicationStatus
from app.shared.enums.document_type import DocumentType
from app.shared.enums.ticket_status import TicketStatus
from app.shared.enums.user_roles import UserRole
from app.shared.enums.job_status import JobStatus
from app.shared.constants.errors import ERR_DUPLICATE_APPLICATION, ERR_MISSING_DOCUMENTS, ERR_JOB_NOT_FOUND
from app.shared.helpers.storage import generate_filename, get_s3_client, build_public_url
from app.shared.constants.storage import MAX_FILE_SIZE_MB, ALLOWED_EXTENSIONS
from app.core.config import settings

router = APIRouter(prefix="/applications", tags=["Applications"])


@router.get("/public/jobs", response_model=StandardResponse[PaginatedResponse[dict]])
async def public_list_jobs(
    q: Optional[str] = None,
    location: Optional[str] = None,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Job).where(
        Job.status == JobStatus.PUBLISHED,
        Job.is_public == True,
        Job.deleted_at.is_(None),
    )
    if q:
        stmt = stmt.where(Job.title.ilike(f"%{q}%"))
    if location:
        stmt = stmt.where(Job.location.ilike(f"%{location}%"))

    total_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_result.scalar_one()

    stmt = stmt.order_by(Job.published_at.desc()).offset(pagination.offset).limit(pagination.limit)
    result = await db.execute(stmt)
    items = []
    for j in result.scalars().all():
        company = await db.execute(select(Company).where(Company.id == j.company_id))
        comp = company.scalar_one_or_none()
        items.append({
            "id": j.id, "title": j.title, "department": j.department,
            "employment_type": j.employment_type.value, "location": j.location,
            "salary_min": j.salary_min, "salary_max": j.salary_max,
            "description": j.description, "apply_code": j.apply_code,
            "company_name": comp.name if comp else None,
            "published_at": j.published_at.isoformat() if j.published_at else None,
        })

    pages = (total + pagination.per_page - 1) // pagination.per_page
    return StandardResponse.ok(data=PaginatedResponse(
        data=items, total=total, page=pagination.page,
        per_page=pagination.per_page, total_pages=pages,
        has_next=pagination.page < pages, has_prev=pagination.page > 1,
    ))


@router.get("/public/jobs/{job_id}", response_model=StandardResponse[dict])
async def public_job_detail(job_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(
        Job.id == job_id, Job.status == JobStatus.PUBLISHED, Job.is_public == True, Job.deleted_at.is_(None)
    ))
    job = result.scalar_one_or_none()
    if not job:
        return StandardResponse.error(message="Job not found", status_code=404)

    reqs = await db.execute(select(Job).where(Job.id == job_id))
    company = await db.execute(select(Company).where(Company.id == job.company_id))
    comp = company.scalar_one_or_none()
    form_fields = await db.execute(select(JobFormField).where(JobFormField.job_id == job_id).order_by(JobFormField.order_index))

    return StandardResponse.ok(data={
        "id": job.id, "title": job.title, "description": job.description,
        "responsibilities": job.responsibilities, "benefits": job.benefits,
        "employment_type": job.employment_type.value, "location": job.location,
        "company_name": comp.name if comp else None,
        "form_fields": [{"field_key": f.field_key, "field_type": f.field_type.value, "label": f.label, "is_required": f.is_required} for f in form_fields.scalars().all()],
    })


@router.post("/public/apply", response_model=StandardResponse[dict])
async def public_apply(
    job_id: int = Form(...),
    email: str = Form(...),
    full_name: str = Form(...),
    phone: Optional[str] = Form(None),
    answers_json: Optional[str] = Form(None),  # JSON string of answers
    cv: UploadFile = File(...),
    documents: Optional[List[UploadFile]] = File(None),
    db: AsyncSession = Depends(get_db),
):
    # Check job exists and is public
    job_result = await db.execute(select(Job).where(
        Job.id == job_id, Job.status == JobStatus.PUBLISHED, Job.deleted_at.is_(None)
    ))
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or not published")

    # Check duplicate
    existing_user = await db.execute(select(User).where(User.email == email))
    applicant = existing_user.scalar_one_or_none()
    if applicant:
        dup = await db.execute(select(Application).where(
            Application.job_id == job_id, Application.applicant_id == applicant.id, Application.deleted_at.is_(None)
        ))
        if dup.scalar_one_or_none() and not job.allow_multiple_apply:
            raise HTTPException(status_code=409, detail=ERR_DUPLICATE_APPLICATION)
    else:
        applicant = User(email=email, full_name=full_name, phone=phone, role=UserRole.APPLICANT)
        db.add(applicant)
        await db.flush()
        await db.refresh(applicant)

    # Create application
    application = Application(
        job_id=job_id,
        applicant_id=applicant.id,
        status=ApplicationStatus.APPLIED,
    )
    db.add(application)
    await db.flush()
    await db.refresh(application)

    # Save answers
    import json
    if answers_json:
        answers = json.loads(answers_json)
        for key, value in answers.items():
            field_result = await db.execute(select(JobFormField).where(JobFormField.job_id == job_id, JobFormField.field_key == key))
            field = field_result.scalar_one_or_none()
            if field:
                answer = ApplicationAnswer(
                    application_id=application.id,
                    form_field_id=field.id,
                    value_text=str(value) if value is not None else None,
                )
                db.add(answer)

    # Save CV
    if cv:
        ext = cv.filename.split(".")[-1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail="Invalid file type")
        content = await cv.read()
        if len(content) > MAX_FILE_SIZE_MB * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large")
        key = generate_filename(cv.filename, "cvs")
        s3 = get_s3_client()
        s3.put_object(Bucket=settings.R2_BUCKET_NAME, Key=key, Body=content, ContentType=cv.content_type or "application/pdf")
        doc = ApplicationDocument(
            application_id=application.id,
            document_type=DocumentType.CV,
            file_name=cv.filename,
            file_url=build_public_url(key),
            file_size=len(content),
            mime_type=cv.content_type or "application/pdf",
        )
        db.add(doc)

    # Save other documents
    if documents:
        for doc_file in documents:
            ext = doc_file.filename.split(".")[-1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                continue
            content = await doc_file.read()
            if len(content) > MAX_FILE_SIZE_MB * 1024 * 1024:
                continue
            key = generate_filename(doc_file.filename, "documents")
            s3 = get_s3_client()
            s3.put_object(Bucket=settings.R2_BUCKET_NAME, Key=key, Body=content, ContentType=doc_file.content_type or "application/pdf")
            doc = ApplicationDocument(
                application_id=application.id,
                document_type=DocumentType.LAINNYA,
                file_name=doc_file.filename,
                file_url=build_public_url(key),
                file_size=len(content),
                mime_type=doc_file.content_type or "application/pdf",
            )
            db.add(doc)

    # Create ticket
    ticket = Ticket(
        application_id=application.id,
        code=generate_ticket_code(),
        status=TicketStatus.OPEN,
        subject=f"Application for {job.title}",
    )
    db.add(ticket)

    # Status log
    log = ApplicationStatusLog(application_id=application.id, to_status=ApplicationStatus.APPLIED.value)
    db.add(log)

    await db.commit()
    await db.refresh(ticket)

    return StandardResponse.ok(data={
        "application_id": application.id,
        "ticket_code": ticket.code,
        "status": ApplicationStatus.APPLIED.value,
    }, message="Application submitted successfully")


@router.get("", response_model=StandardResponse[PaginatedResponse[dict]])
async def list_applications(
    job_id: Optional[int] = None,
    status: Optional[ApplicationStatus] = None,
    q: Optional[str] = None,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_hr),
):
    stmt = select(Application).join(Job).where(
        Job.company_id == current_user.company_id,
        Application.deleted_at.is_(None),
    )
    if job_id:
        stmt = stmt.where(Application.job_id == job_id)
    if status:
        stmt = stmt.where(Application.status == status)
    if q:
        stmt = stmt.join(User).where(User.full_name.ilike(f"%{q}%"))

    total_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_result.scalar_one()

    stmt = stmt.order_by(Application.created_at.desc()).offset(pagination.offset).limit(pagination.limit)
    result = await db.execute(stmt)
    items = []
    for app in result.scalars().all():
        items.append({
            "id": app.id, "job_id": app.job_id, "applicant_id": app.applicant_id,
            "status": app.status.value, "created_at": app.created_at.isoformat() if app.created_at else None,
        })

    pages = (total + pagination.per_page - 1) // pagination.per_page
    return StandardResponse.ok(data=PaginatedResponse(
        data=items, total=total, page=pagination.page,
        per_page=pagination.per_page, total_pages=pages,
        has_next=pagination.page < pages, has_prev=pagination.page > 1,
    ))


@router.patch("/{application_id}/status", response_model=StandardResponse[dict])
async def update_application_status(
    application_id: int,
    new_status: ApplicationStatus,
    reason: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_hr),
):
    result = await db.execute(select(Application).join(Job).where(
        Application.id == application_id,
        Job.company_id == current_user.company_id,
    ))
    application = result.scalar_one_or_none()
    if not application:
        return StandardResponse.error(message="Application not found", status_code=404)

    old_status = application.status
    application.status = new_status

    log = ApplicationStatusLog(
        application_id=application.id,
        from_status=old_status.value if old_status else None,
        to_status=new_status.value,
        changed_by=current_user.id,
        reason=reason,
    )
    db.add(log)
    await db.commit()

    return StandardResponse.ok(data={
        "application_id": application.id,
        "old_status": old_status.value if old_status else None,
        "new_status": new_status.value,
    })
