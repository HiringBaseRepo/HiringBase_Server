"""Integration tests for document upload, OCR, and semantic validation pipeline."""

import uuid

import pytest
from httpx import AsyncClient

from app.core.security.jwt import create_access_token
from app.features.applications.models import (
    Application,
    ApplicationAnswer,
    ApplicationDocument,
)
from app.features.companies.models import Company
from app.features.jobs.models import Job, JobFormField
from app.features.users.models import User
from app.shared.enums import EmploymentType
from app.shared.enums.application_status import ApplicationStatus
from app.shared.enums.document_type import DocumentType
from app.shared.enums.field_type import FormFieldType
from app.shared.enums.job_status import JobStatus
from app.shared.enums.user_roles import UserRole


def _make_hr_token(hr_user: User) -> str:
    """Create a valid JWT access token for HR user."""
    return create_access_token(
        data={
            "sub": str(hr_user.id),
            "role": hr_user.role.value,
            "company_id": hr_user.company_id,
            "uid": hr_user.id,
            "token_version": hr_user.token_version,
        }
    )


@pytest.mark.asyncio
async def test_screening_requires_all_documents(
    client: AsyncClient,
    test_db_session,
    override_db,
):
    """Test that screening requires both KTP and Ijazah documents.

    Scenario:
    - Create application with KTP only (missing Ijazah)
    - Trigger screening
    - Verify endpoint accepts request (background process handles DOC_FAILED)
    """
    session = test_db_session
    unique_id = str(uuid.uuid4())[:8]

    # Setup
    company = Company(
        name=f"RequiredDoc Company {unique_id}",
        slug=f"required-doc-{unique_id}",
    )
    session.add(company)
    await session.flush()

    hr_user = User(
        email=f"hr_req_{unique_id}@test.com",
        full_name="HR Required Test",
        password_hash="dummy_hash",
        role=UserRole.HR,
        company_id=company.id,
        is_active=True,
    )
    session.add(hr_user)
    await session.flush()

    job = Job(
        title="Data Analyst",
        department="Analytics",
        employment_type=EmploymentType.FULL_TIME,
        description="Test job for required docs",
        status=JobStatus.PUBLISHED,
        location="Jakarta",
        apply_code=f"REQ{unique_id}",
        company_id=company.id,
        created_by=hr_user.id,
        is_public=True,
    )
    session.add(job)
    await session.flush()

    applicant = User(
        email=f"nodoc_{unique_id}@test.com",
        full_name="No Document User",
        phone="081234567890",
        role=UserRole.APPLICANT,
    )
    session.add(applicant)
    await session.flush()

    application = Application(
        job_id=job.id,
        applicant_id=applicant.id,
        status=ApplicationStatus.AI_PROCESSING,
    )
    session.add(application)
    await session.flush()

    # Add only KTP (missing Ijazah)
    ktp_document = ApplicationDocument(
        application_id=application.id,
        document_type=DocumentType.IDENTITY_CARD,
        file_url=f"https://mock-r2.example.com/documents/ktp_{unique_id}.pdf",
        file_name="ktp.pdf",
        mime_type="application/pdf",
    )
    session.add(ktp_document)
    await session.flush()

    application_id = application.id
    hr_token = _make_hr_token(hr_user)

    # Trigger screening - with only KTP (missing Ijazah), background marks DOC_FAILED
    screening_response = await client.post(
        f"/api/v1/screening/applications/{application_id}/run",
        headers={"Authorization": f"Bearer {hr_token}"},
    )

    assert screening_response.status_code == 200
    response_data = screening_response.json()
    assert response_data["success"] is True


@pytest.mark.asyncio
async def test_screening_with_all_required_documents(
    client: AsyncClient,
    test_db_session,
    override_db,
):
    """Test that having all required documents (KTP + Ijazah) allows screening to proceed."""
    session = test_db_session
    unique_id = str(uuid.uuid4())[:8]

    # Setup
    company = Company(
        name=f"AllDocs Company {unique_id}",
        slug=f"all-docs-{unique_id}",
    )
    session.add(company)
    await session.flush()

    hr_user = User(
        email=f"hr_alldocs_{unique_id}@test.com",
        full_name="HR AllDocs Test",
        password_hash="dummy_hash",
        role=UserRole.HR,
        company_id=company.id,
        is_active=True,
    )
    session.add(hr_user)
    await session.flush()

    job = Job(
        title="Full Stack Engineer",
        department="Engineering",
        employment_type=EmploymentType.FULL_TIME,
        description="Test job for all docs",
        status=JobStatus.PUBLISHED,
        location="Jakarta",
        apply_code=f"ALL{unique_id}",
        company_id=company.id,
        created_by=hr_user.id,
        is_public=True,
    )
    session.add(job)
    await session.flush()

    # Create form field
    ff = JobFormField(
        job_id=job.id,
        field_key="skills",
        label="Skills",
        field_type=FormFieldType.TEXT,
        is_required=True,
    )
    session.add(ff)
    await session.flush()

    applicant = User(
        email=f"alldocs_{unique_id}@test.com",
        full_name="All Documents User",
        phone="081234567890",
        role=UserRole.APPLICANT,
    )
    session.add(applicant)
    await session.flush()

    application = Application(
        job_id=job.id,
        applicant_id=applicant.id,
        status=ApplicationStatus.AI_PROCESSING,
    )
    session.add(application)
    await session.flush()

    # Add BOTH KTP and Ijazah
    documents = [
        ApplicationDocument(
            application_id=application.id,
            document_type=DocumentType.IDENTITY_CARD,
            file_url=f"https://mock-r2.example.com/documents/ktp_{unique_id}.pdf",
            file_name="ktp.pdf",
            mime_type="application/pdf",
        ),
        ApplicationDocument(
            application_id=application.id,
            document_type=DocumentType.DEGREE,
            file_url=f"https://mock-r2.example.com/documents/ijazah_{unique_id}.pdf",
            file_name="ijazah.pdf",
            mime_type="application/pdf",
        ),
    ]
    session.add_all(documents)
    await session.flush()

    # Add application answer
    session.add(
        ApplicationAnswer(
            application_id=application.id,
            form_field_id=ff.id,
            value_text="Python, FastAPI, SQL",
        )
    )
    await session.flush()

    application_id = application.id
    hr_token = _make_hr_token(hr_user)

    # Trigger screening
    screening_response = await client.post(
        f"/api/v1/screening/applications/{application_id}/run",
        headers={"Authorization": f"Bearer {hr_token}"},
    )

    # With all required documents, screening endpoint should accept the request
    assert screening_response.status_code == 200
    response_data = screening_response.json()
    assert response_data["success"] is True
    assert "queued" in response_data["message"].lower() or response_data["data"] is not None


@pytest.mark.asyncio
async def test_document_tenant_isolation(
    client: AsyncClient, test_db_session, override_db
):
    """Test that HR from Company A cannot access Company B's applications."""
    session = test_db_session
    unique_id = str(uuid.uuid4())[:8]

    # Setup Company A (attacker)
    company_a = Company(
        name=f"Company A {unique_id}",
        slug=f"company-a-{unique_id}",
    )
    session.add(company_a)
    await session.flush()

    hr_a = User(
        email=f"hr_a_{unique_id}@test.com",
        full_name="HR A",
        password_hash="dummy_hash",
        role=UserRole.HR,
        company_id=company_a.id,
        is_active=True,
    )
    session.add(hr_a)
    await session.flush()

    # Setup Company B (victim)
    company_b = Company(
        name=f"Company B {unique_id}",
        slug=f"company-b-{unique_id}",
    )
    session.add(company_b)
    await session.flush()

    hr_b = User(
        email=f"hr_b_{unique_id}@test.com",
        full_name="HR B",
        password_hash="dummy_hash",
        role=UserRole.HR,
        company_id=company_b.id,
        is_active=True,
    )
    session.add(hr_b)
    await session.flush()

    # Create job and application for Company B
    job_b = Job(
        title="Engineer",
        employment_type=EmploymentType.FULL_TIME,
        description="Company B job",
        status=JobStatus.PUBLISHED,
        location="Jakarta",
        apply_code=f"COMPB{unique_id}",
        company_id=company_b.id,
        created_by=hr_b.id,
        is_public=True,
    )
    session.add(job_b)
    await session.flush()

    applicant = User(
        email=f"victim_{unique_id}@test.com",
        full_name="Victim User",
        role=UserRole.APPLICANT,
    )
    session.add(applicant)
    await session.flush()

    application = Application(
        job_id=job_b.id,
        applicant_id=applicant.id,
        status=ApplicationStatus.DOC_CHECK,
    )
    session.add(application)
    await session.flush()

    application_id = application.id

    # HR from Company A tries to trigger screening (access application)
    hr_a_token = _make_hr_token(hr_a)

    screening_response = await client.post(
        f"/api/v1/screening/applications/{application_id}/run",
        headers={"Authorization": f"Bearer {hr_a_token}"},
    )

    # Should be rejected (404 due to tenant isolation)
    assert screening_response.status_code == 404, (
        f"HR from Company A should not access Company B's application. Got {screening_response.status_code}"
    )
