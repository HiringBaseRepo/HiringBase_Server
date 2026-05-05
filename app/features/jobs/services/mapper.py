"""Mapping logic for jobs service."""

from typing import Any

from app.features.jobs.schemas.schema import (
    JobFormFieldItem,
    JobKnockoutRuleItem,
    JobListItem,
    JobRequirementItem,
)


def map_job_to_list_item(job: Any) -> JobListItem:
    """Map job to list item.

    Args:
        job: Job object

    Returns:
        JobListItem schema
    """
    return JobListItem(
        id=job.id,
        title=job.title,
        department=job.department,
        employment_type=job.employment_type,
        status=job.status,
        location=job.location,
        apply_code=job.apply_code,
        published_at=job.published_at.isoformat() if job.published_at else None,
        created_at=job.created_at.isoformat() if job.created_at else None,
    )


def map_requirement_to_item(requirement: Any) -> JobRequirementItem:
    """Map requirement to item.

    Args:
        requirement: Requirement object

    Returns:
        JobRequirementItem schema
    """
    return JobRequirementItem.model_validate(requirement, from_attributes=True)


def map_form_field_to_item(form_field: Any) -> JobFormFieldItem:
    """Map form field to item.

    Args:
        form_field: Form field object

    Returns:
        JobFormFieldItem schema
    """
    return JobFormFieldItem.model_validate(form_field, from_attributes=True)


def map_knockout_rule_to_item(knockout_rule: Any) -> JobKnockoutRuleItem:
    """Map knockout rule to item.

    Args:
        knockout_rule: Knockout rule object

    Returns:
        JobKnockoutRuleItem schema
    """
    return JobKnockoutRuleItem.model_validate(knockout_rule, from_attributes=True)
