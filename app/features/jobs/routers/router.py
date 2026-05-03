"""Vacancy Management API."""
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.base import get_db
from app.features.auth.dependencies.auth import require_hr
from app.features.jobs.schemas.schema import (
    AddJobRequirementsRequest,
    CreateJobStep1Request,
    JobCloseResponse,
    JobDetailResponse,
    JobListItem,
    JobPublishResponse,
    JobStepResponse,
    PublishJobRequest,
    SetupJobFormRequest,
)
from app.features.jobs.services.service import (
    add_job_requirements as add_job_requirements_service,
    close_job as close_job_service,
    create_job_step1 as create_job_step1_service,
    get_job_detail as get_job_detail_service,
    list_jobs as list_jobs_service,
    publish_job as publish_job_service,
    setup_job_form as setup_job_form_service,
)
from app.shared.schemas.response import StandardResponse, PaginatedResponse
from app.core.utils.pagination import PaginationParams
from app.shared.enums.job_status import JobStatus

router = APIRouter(prefix="/jobs", tags=["Jobs / Vacancies"])


@router.post("/create-step1", response_model=StandardResponse[JobStepResponse])
async def create_job_step1(
    data: CreateJobStep1Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_hr),
):
    result = await create_job_step1_service(
        db,
        current_user=current_user,
        data=data,
    )
    return StandardResponse.ok(data=result, message="Step 1 saved")


@router.post("/{job_id}/step2-requirements", response_model=StandardResponse[JobStepResponse])
async def add_job_requirements(
    job_id: int,
    data: AddJobRequirementsRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_hr),
):
    result = await add_job_requirements_service(
        db,
        current_user=current_user,
        job_id=job_id,
        data=data,
    )
    return StandardResponse.ok(data=result)


@router.post("/{job_id}/step3-form", response_model=StandardResponse[JobStepResponse])
async def setup_job_form(
    job_id: int,
    data: SetupJobFormRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_hr),
):
    result = await setup_job_form_service(
        db,
        current_user=current_user,
        job_id=job_id,
        data=data,
    )
    return StandardResponse.ok(data=result)


@router.post("/{job_id}/step4-publish", response_model=StandardResponse[JobPublishResponse])
async def publish_job(
    job_id: int,
    data: PublishJobRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_hr),
):
    result = await publish_job_service(
        db,
        current_user=current_user,
        job_id=job_id,
        data=data,
    )
    return StandardResponse.ok(data=result)


@router.get("", response_model=StandardResponse[PaginatedResponse[JobListItem]])
async def list_jobs(
    status: Optional[JobStatus] = None,
    q: Optional[str] = None,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_hr),
):
    result = await list_jobs_service(
        db,
        current_user=current_user,
        pagination=pagination,
        status=status,
        q=q,
    )
    return StandardResponse.ok(data=result)


@router.get("/{job_id}", response_model=StandardResponse[JobDetailResponse])
async def get_job_detail(job_id: int, db: AsyncSession = Depends(get_db), current_user=Depends(require_hr)):
    result = await get_job_detail_service(db, current_user=current_user, job_id=job_id)
    return StandardResponse.ok(data=result)


@router.patch("/{job_id}/close", response_model=StandardResponse[JobCloseResponse])
async def close_job(job_id: int, db: AsyncSession = Depends(get_db), current_user=Depends(require_hr)):
    result = await close_job_service(db, current_user=current_user, job_id=job_id)
    return StandardResponse.ok(data=result)
