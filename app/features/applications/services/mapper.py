"""Mapping logic for applications service."""

from typing import Any
from app.features.applications.schemas.schema import PublicJobItem
from app.shared.helpers.localization import get_label


def map_job_to_public_item(job: Any, company: Any) -> PublicJobItem:
    """Map job to public job item.

    Args:
        job: Job object
        company: Company object

    Returns:
        PublicJobItem schema
    """
    return PublicJobItem(
        id=job.id,
        title=job.title,
        department=job.department,
        employment_type=job.employment_type.value,
        employment_type_label=get_label(job.employment_type),
        location=job.location,
        salary_min=job.salary_min,
        salary_max=job.salary_max,
        description=job.description,
        apply_code=job.apply_code,
        company_name=company.name if company else None,
        published_at=job.published_at.isoformat() if job.published_at else None,
    )


def map_jobs_to_public_items(jobs: list[Any]) -> list[PublicJobItem]:
    """Map list of jobs to public job items.

    Args:
        jobs: List of job objects

    Returns:
        List of PublicJobItem schemas
    """
    return [map_job_to_public_item(job, None) for job in jobs]
