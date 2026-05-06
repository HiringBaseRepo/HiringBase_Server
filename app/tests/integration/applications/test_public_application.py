"""Integration tests for public application submission and ticket tracking."""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.features.applications.models import Application
from app.features.tickets.models import Ticket
from app.shared.enums.application_status import ApplicationStatus
from app.shared.enums.ticket_status import TicketStatus
from app.features.companies.models import Company
from app.features.jobs.models import Job, JobFormField
from app.features.users.models import User
from app.shared.enums import EmploymentType
from app.shared.enums.field_type import FormFieldType
from app.shared.enums.job_status import JobStatus
from app.shared.enums.user_roles import UserRole


@pytest.mark.asyncio
async def test_public_application_submission(
    client: AsyncClient, test_db_session, override_db, mock_r2, mock_ocr_engine
):
    """Test complete public application submission flow."""
    session = test_db_session
    unique_id = str(uuid.uuid4())[:8]

    # Setup test data
    company = Company(
        name=f"Test Company {unique_id}",
        slug=f"test-company-{unique_id}",
        website="test.com",
        logo_url="https://test.com/logo.png",
    )
    session.add(company)
    await session.flush()

    user = User(
        email=f"hr_{unique_id}@test.com",
        full_name="HR Test",
        role=UserRole.HR,
        company_id=company.id,
    )
    session.add(user)
    await session.flush()

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

    # Create form fields
    form_fields = [
        JobFormField(
            job_id=job.id,
            field_key="full_name",
            label="Full Name",
            field_type=FormFieldType.TEXT,
            is_required=True,
            order_index=1,
        ),
        JobFormField(
            job_id=job.id,
            field_key="email",
            label="Email",
            field_type=FormFieldType.TEXT,
            is_required=True,
            order_index=2,
        ),
    ]
    session.add_all(form_fields)
    await session.flush()
    job_id = job.id

    # Prepare application data
    application_data = {
        "job_id": job_id,
        "full_name": "John Doe",
        "email": f"john_{unique_id}@test.com",
        "phone": "081234567890",
        "answers_json": f'{{"experience_years": "3", "education_level": "s1", "full_name": "John Doe", "email": "john_{unique_id}@test.com"}}',
    }

    # Test the endpoint
    response = await client.post(
        "/api/v1/applications/public/apply",
        data=application_data,  # form-data
    )

    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    ticket_code = data["data"]["ticket_code"]
    assert ticket_code.startswith("TKT-")

    # Verify data in database using the same session
    user_stmt = select(User).where(User.email == f"john_{unique_id}@test.com")
    user_result = await session.execute(user_stmt)
    user_obj = user_result.scalar_one_or_none()
    assert user_obj is not None

    app_stmt = select(Application).where(Application.applicant_id == user_obj.id)
    app_result = await session.execute(app_stmt)
    assert app_result.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_duplicate_application_prevention(
    client: AsyncClient, test_db_session, override_db, mock_r2
):
    """Test that a candidate cannot apply twice for the same job."""
    session = test_db_session
    unique_id = str(uuid.uuid4())[:8]

    # Setup test data
    company = Company(
        name=f"Test Company {unique_id}",
        slug=f"test-company-{unique_id}",
    )
    session.add(company)
    await session.flush()

    job = Job(
        title="Software Engineer",
        status=JobStatus.PUBLISHED,
        employment_type=EmploymentType.FULL_TIME,
        description="Test job description",
        company_id=company.id,
        is_public=True,
    )
    session.add(job)
    await session.flush()
    job_id = job.id

    application_data = {
        "job_id": job_id,
        "full_name": "John Duplicate",
        "email": f"duplicate_{unique_id}@test.com",
    }

    # First application
    resp1 = await client.post("/api/v1/applications/public/apply", data=application_data)
    assert resp1.status_code == 200

    # Second application with same email and job_id
    resp2 = await client.post("/api/v1/applications/public/apply", data=application_data)
    
    # Should be rejected with 409 Conflict
    assert resp2.status_code == 409
    resp2_data = resp2.json()
    assert resp2_data.get("success") is False or resp2.status_code == 409


@pytest.mark.asyncio
async def test_ticket_status_tracking(client: AsyncClient, test_db_session, override_db):
    """Test ticket-based status tracking without authentication."""
    session = test_db_session
    unique_id = str(uuid.uuid4())[:8]

    # Setup test data
    company = Company(
        name=f"Test Company {unique_id}",
        slug=f"test-company-{unique_id}",
    )
    session.add(company)
    await session.flush()

    job = Job(
        title="Software Engineer",
        status=JobStatus.PUBLISHED,
        employment_type=EmploymentType.FULL_TIME,
        description="Test job description",
        company_id=company.id,
        is_public=True,
    )
    session.add(job)
    await session.flush()

    applicant = User(
        email=f"john_{unique_id}@test.com",
        full_name="John Doe",
        role=UserRole.APPLICANT,
    )
    session.add(applicant)
    await session.flush()

    application = Application(
        job_id=job.id,
        applicant_id=applicant.id,
        status=ApplicationStatus.APPLIED,
    )
    session.add(application)
    await session.flush()

    ticket = Ticket(
        application_id=application.id,
        code=f"TKT-2024-{unique_id}",
        status=TicketStatus.OPEN,
    )
    session.add(ticket)
    await session.flush()
    ticket_code = ticket.code

    # Test ticket tracking endpoint
    response = await client.get(f"/api/v1/tickets/track/{ticket_code}")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["ticket_code"] == ticket_code
