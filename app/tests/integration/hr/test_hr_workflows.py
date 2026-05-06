"""Integration tests for HR workflows including vacancy management and screening."""

import uuid
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient

from app.core.security.hashing import get_password_hash
from app.features.applications.models import Application, ApplicationAnswer
from app.features.companies.models import Company
from app.features.jobs.models import Job, JobFormField, JobKnockoutRule, JobRequirement
from app.features.users.models import User
from app.shared.enums import EmploymentType
from app.shared.enums.application_status import ApplicationStatus
from app.shared.enums.field_type import FormFieldType
from app.shared.enums.job_status import JobStatus
from app.shared.enums.user_roles import UserRole


@pytest.mark.asyncio
async def test_vacancy_lifecycle(client: AsyncClient, auth_headers, override_db):
    """Test complete vacancy lifecycle: creation, publishing, and knockout rule setup."""
    unique_id = str(uuid.uuid4())[:8]

    # Test job creation
    job_data = {
        "title": "Software Engineer",
        "department": "Engineering",
        "employment_type": "full_time",
        "location": "Jakarta",
        "description": "Test job description",
    }

    response = await client.post("/api/v1/jobs/create-step1", json=job_data, headers=auth_headers["headers"])

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    job_id = data["data"]["job_id"]

    # Test job publishing
    publish_data = {
        "mode": "public"
    }
    publish_response = await client.post(
        f"/api/v1/jobs/{job_id}/step4-publish", json=publish_data, headers=auth_headers["headers"]
    )

    assert publish_response.status_code == 200
    publish_data_resp = publish_response.json()
    assert publish_data_resp["success"] is True
    assert publish_data_resp["data"]["status"] == JobStatus.PUBLISHED.value

    # Test knockout rule creation
    rule_params = {
        "rule_name": "Min Experience",
        "rule_type": "experience",
        "operator": "gte",
        "target_value": "2",
        "field_key": "experience_years",
        "action": "auto_reject",
    }
    rule_response = await client.post(
        f"/api/v1/screening/{job_id}/knockout-rules", params=rule_params, headers=auth_headers["headers"]
    )

    assert rule_response.status_code == 200
    rule_data_resp = rule_response.json()
    assert rule_data_resp["success"] is True


@pytest.mark.asyncio
async def test_hr_screening_view(
    client: AsyncClient, auth_headers, test_db_session, override_db, mock_groq, mock_ocr_engine
):
    """Test HR viewing AI screening results for candidates."""
    session = test_db_session
    unique_id = str(uuid.uuid4())[:8]

    # Setup test data
    company = auth_headers["company"]
    user = auth_headers["user"]

    # Create job
    job = Job(
        title="Software Engineer",
        department="Engineering",
        employment_type=EmploymentType.FULL_TIME,
        description="Test job description",
        status=JobStatus.PUBLISHED,
        location="Jakarta",
        apply_code=f"TEST{unique_id}",
        company_id=company.id,
        created_by=user.id,
        is_public=True,
    )
    session.add(job)
    await session.flush()

    # Create applicant user
    applicant = User(
        email=f"john_{unique_id}@test.com",
        full_name="John Doe",
        phone="081234567890",
        role=UserRole.APPLICANT,
    )
    session.add(applicant)
    await session.flush()

    # Create application
    application = Application(
        job_id=job.id,
        applicant_id=applicant.id,
        status=ApplicationStatus.AI_PROCESSING,
    )
    session.add(application)
    await session.flush()

    # Create form field
    form_field = JobFormField(
        job_id=job.id,
        field_key="skills",
        label="Skills",
        field_type=FormFieldType.TEXT,
        is_required=True,
    )
    session.add(form_field)
    await session.flush()

    # Create application answer
    answer = ApplicationAnswer(
        application_id=application.id,
        form_field_id=form_field.id,
        value_text="Python, SQL, FastApi",
    )
    session.add(answer)
    await session.flush()

    application_id = application.id

    # Test triggering screening (POST /run)
    response = await client.post(
        f"/api/v1/screening/applications/{application_id}/run", headers=auth_headers["headers"]
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_tenant_isolation(client: AsyncClient, auth_headers, test_db_session, override_db):
    """Test that HR from Company A cannot access Company B's data."""
    session = test_db_session
    unique_id = str(uuid.uuid4())[:8]

    # Setup Company B data
    # Create Company B
    company_b = Company(
        name=f"Company B {unique_id}",
        slug=f"company-b-{unique_id}",
        website="company-b.com",
        logo_url="https://company-b.com/logo.png",
    )
    session.add(company_b)
    await session.flush()

    # Create job for Company B
    job_b = Job(
        title="Software Engineer",
        department="Engineering",
        employment_type=EmploymentType.FULL_TIME,
        status=JobStatus.PUBLISHED,
        location="Jakarta",
        apply_code=f"TESTB{unique_id}",
        description="Test job for Company B",
        company_id=company_b.id,
        is_public=True,
    )
    session.add(job_b)
    await session.flush()

    job_b_id = job_b.id

    # Try to access Company B's job with Company A HR credentials (from auth_headers)
    response = await client.get(f"/api/v1/jobs/{job_b_id}", headers=auth_headers["headers"])

    # Should return 404 due to tenant isolation (get_job_for_company filters by company_id)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_interview_scheduling(client: AsyncClient, auth_headers, test_db_session, override_db):
    """Test interview scheduling workflow."""
    session = test_db_session
    unique_id = str(uuid.uuid4())[:8]

    # Setup test data
    company = auth_headers["company"]
    user = auth_headers["user"]

    # Create job
    job = Job(
        title="Software Engineer",
        department="Engineering",
        employment_type=EmploymentType.FULL_TIME,
        description="Test job description",
        status=JobStatus.PUBLISHED,
        location="Jakarta",
        apply_code=f"TEST{unique_id}",
        company_id=company.id,
        created_by=user.id,
        is_public=True,
    )
    session.add(job)
    await session.flush()

    # Create applicant user
    applicant = User(
        email=f"john_{unique_id}@test.com",
        full_name="John Doe",
        phone="081234567890",
        role=UserRole.APPLICANT,
    )
    session.add(applicant)
    await session.flush()

    # Create application
    application = Application(
        job_id=job.id,
        applicant_id=applicant.id,
        status=ApplicationStatus.AI_PASSED,
    )
    session.add(application)
    await session.flush()

    application_id = application.id

    # Test interview scheduling
    interview_data = {
        "application_id": application_id,
        "scheduled_at": (datetime.utcnow() + timedelta(days=1)).isoformat(),
        "interviewer_id": user.id,
        "notes": "Technical interview",
        "meeting_url": "https://zoom.us/test-meeting",
    }

    response = await client.post(
        "/api/v1/interviews", json=interview_data, headers=auth_headers["headers"]
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "interview_id" in data["data"]
