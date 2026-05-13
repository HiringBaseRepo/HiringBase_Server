"""Validation logic for applications service."""

import json
from fastapi import UploadFile

from app.core.exceptions import (
    BaseDomainException,
    DuplicateApplicationException,
    JobNotFoundException,
    MissingDocumentsException,
)
from app.features.applications.repositories.repository import (
    get_application_by_job_and_applicant,
    get_form_fields_by_job_id,
    get_knockout_rules_by_job_id,
    get_published_job_by_id,
    get_user_by_email,
)
from app.shared.constants.errors import ERR_DUPLICATE_APPLICATION


async def validate_public_apply_requirements(
    db,
    data,
    documents_data: list[dict] | None = None,
) -> None:
    """Validate public application requirements.

    Args:
        db: Database session
        data: Public apply command data
        documents_data: List of dicts containing 'type' and 'file'

    Raises:
        BaseDomainException: If validation fails
    """
    # Validate job exists and is published
    job = await get_published_job_by_id(db, data.job_id)
    if not job:
        raise JobNotFoundException("Lowongan tidak ditemukan atau belum dipublikasikan")

    # VALIDATION 1: Mandatory Form Fields
    form_fields = await get_form_fields_by_job_id(db, job_id=data.job_id)
    answers = json.loads(data.answers_json) if data.answers_json else {}
    for field in form_fields:
        if field.is_required and not answers.get(field.field_key):
            raise BaseDomainException(f"Field '{field.label}' wajib diisi")

    # VALIDATION 2: Required Documents
    knockout_rules = await get_knockout_rules_by_job_id(db, job_id=data.job_id)
    required_docs = [
        r.target_value.lower()
        for r in knockout_rules
        if r.rule_type == "document" and r.is_active
    ]

    uploaded_doc_types = (
        [doc["type"].value for doc in documents_data] if documents_data else []
    )
    for req_doc in required_docs:
        found = any(req_doc == doc_type for doc_type in uploaded_doc_types)
        if not found:
            raise MissingDocumentsException([req_doc])

    # VALIDATION 3: Duplicate application check
    applicant = await get_user_by_email(db, data.email)
    if applicant:
        duplicate = await get_application_by_job_and_applicant(
            db,
            job_id=data.job_id,
            applicant_id=applicant.id,
        )
        if duplicate and not job.allow_multiple_apply:
            raise DuplicateApplicationException()
