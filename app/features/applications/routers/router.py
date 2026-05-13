"""Public Applicant + Application Management API."""

from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.base import get_db
from app.core.exceptions import (
    ApplicationNotFoundException,
    FileTooLargeException,
    InvalidFileTypeException,
    JobNotFoundException,
)
from app.core.utils.pagination import PaginationParams
from app.features.applications.schemas.schema import (
    ApplicationListItem,
    ApplicationStatusUpdateResponse,
    PublicApplyCommand,
    PublicApplyResponse,
    PublicJobDetailResponse,
    PublicJobItem,
    ApplicationDetailResponse,
)
from app.features.applications.services.service import (
    get_public_job_detail as get_public_job_detail_service,
)
from app.features.applications.services.service import (
    list_applications as list_applications_service,
    get_application_detail as get_application_detail_service,
)
from app.features.applications.services.service import (
    list_public_jobs as list_public_jobs_service,
)
from app.features.applications.services.service import (
    public_apply as public_apply_service,
)
from app.features.applications.services.service import (
    update_application_status as update_application_status_service,
)
from app.features.auth.dependencies.auth import require_hr
from app.shared.enums.application_status import ApplicationStatus
from app.shared.enums.document_type import DocumentType
from app.shared.helpers.localization import get_label
from app.shared.schemas.response import PaginatedResponse, StandardResponse

router = APIRouter(prefix="/applications", tags=["Applications"])


@router.get(
    "/public/jobs", response_model=StandardResponse[PaginatedResponse[PublicJobItem]]
)
async def public_list_jobs(
    q: Optional[str] = None,
    location: Optional[str] = None,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await list_public_jobs_service(
        db, pagination=pagination, q=q, location=location
    )
    return StandardResponse.ok(data=result)


@router.get(
    "/public/jobs/{job_id}", response_model=StandardResponse[PublicJobDetailResponse]
)
async def public_job_detail(job_id: int, db: AsyncSession = Depends(get_db)):
    result = await get_public_job_detail_service(db, job_id)
    return StandardResponse.ok(data=result)


@router.post("/public/apply", response_model=StandardResponse[PublicApplyResponse])
async def public_apply(
    request: Request,
    job_id: int = Form(...),
    email: str = Form(...),
    full_name: str = Form(...),
    phone: Optional[str] = Form(None),
    answers_json: Optional[str] = Form(None),  # JSON string of answers
    db: AsyncSession = Depends(get_db),
):
    form_data = await request.form()
    documents_data = []
    for key, value in form_data.multi_items():
        if hasattr(value, "filename") and value.filename:
            doc_type = DocumentType.OTHERS
            if key.startswith("file_"):
                enum_key = key.replace("file_", "")
                if enum_key in DocumentType._member_names_:
                    doc_type = DocumentType[enum_key]
            documents_data.append({"type": doc_type, "file": value})
    
    command = PublicApplyCommand(
        job_id=job_id,
        email=email,
        full_name=full_name,
        phone=phone,
        answers_json=answers_json,
    )
    result = await public_apply_service(db, data=command, documents_data=documents_data)
    return StandardResponse.ok(
        data=result, message=get_label("Application submitted successfully")
    )


@router.get("", response_model=StandardResponse[PaginatedResponse[ApplicationListItem]])
async def list_applications(
    job_id: Optional[int] = None,
    status: Optional[ApplicationStatus] = None,
    q: Optional[str] = None,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_hr),
):
    result = await list_applications_service(
        db,
        current_user=current_user,
        pagination=pagination,
        job_id=job_id,
        status_filter=status,
        q=q,
    )
    return StandardResponse.ok(data=result)


@router.patch(
    "/{application_id}/status",
    response_model=StandardResponse[ApplicationStatusUpdateResponse],
)
async def update_application_status(
    application_id: int,
    new_status: ApplicationStatus,
    reason: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_hr),
):
    result = await update_application_status_service(
        db,
        current_user=current_user,
        application_id=application_id,
        new_status=new_status,
        reason=reason,
    )
    return StandardResponse.ok(data=result)


@router.get("/{application_id}", response_model=StandardResponse[ApplicationDetailResponse])
async def get_application_detail(
    application_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_hr),
):
    result = await get_application_detail_service(
        db, current_user=current_user, application_id=application_id
    )
    return StandardResponse.ok(data=result)
