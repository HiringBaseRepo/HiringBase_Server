"""Integration tests for public application submission and ticket tracking."""

import uuid

import pytest
from httpx import AsyncClient

from app.core.database.base import AsyncSessionLocal
from app.core.security.hashing import get_password_hash
from app.features.companies.models import Company
from app.features.jobs.models import Job, JobFormField
from app.features.users.models import User
from app.shared.enums.field_type import FormFieldType
from app.shared.enums.job_status import JobStatus
from app.shared.enums.user_roles import UserRole


@pytest.mark.asyncio
async def test_public_application_submission(
    client: AsyncClient, mock_r2, mock_ocr_engine
):
    """Test complete public application submission flow."""
    unique_id = str(uuid.uuid4())[:8]

    # Setup test data
    async with AsyncSessionLocal() as session:
        # Create company
        company = Company(
            name=f"Test Company {unique_id}",
            slug=f"test-company-{unique_id}",
            website="test.com",
            logo_url="https://test.com/logo.png",
        )
        session.add(company)
        await session.commit()

        # Create HR user
        user = User(
            email=f"hr_{unique_id}@test.com",
            password_hash=get_password_hash("password123"),
            full_name="HR Test",
            role=UserRole.HR,
            company_id=company.id,
        )
        session.add(user)
        await session.commit()

        # Create job
        job = Job(
            title="Software Engineer",
            department="Engineering",
            employment_type="FULL_TIME",
            status=JobStatus.PUBLISHED,
            location="Jakarta",
            apply_code=f"TEST{unique_id}",
            description="Test job description",
            company_id=company.id,
            created_by=user.id,
            is_public=True,
        )
        session.add(job)
        await session.commit()

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
                field_type=FormFieldType.EMAIL,
                is_required=True,
                order_index=2,
            ),
            JobFormField(
                job_id=job.id,
                field_key="experience_years",
                label="Years of Experience",
                field_type=FormFieldType.NUMBER,
                is_required=True,
                order_index=3,
            ),
            JobFormField(
                job_id=job.id,
                field_key="education_level",
                label="Education Level",
                field_type=FormFieldType.TEXT,
                is_required=True,
                order_index=4,
            ),
        ]
        session.add_all(form_fields)
        await session.commit()

        job_id = job.id

    # Prepare application data
    application_data = {
        "job_id": job_id,
        "apply_code": f"TEST{unique_id}",
        "full_name": "John Doe",
        "email": f"john_{unique_id}@test.com",
        "experience_years": "3",
        "education_level": "s1",
        "phone": "081234567890",
    }

    # Submit application
    response = await client.post(
        f"/api/v1/applications/public/jobs/{job_id}/apply", data=application_data
    )

    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "ticket_code" in data["data"]

    # Verify ticket format
    ticket_code = data["data"]["ticket_code"]
    assert ticket_code.startswith("TKT-")
    assert len(ticket_code.split("-")) == 3

    # Verify application was created in database
    async with AsyncSessionLocal() as verify_session:
        from app.features.applications.models import Application
        from app.features.tickets.models import Ticket

        # Check application exists
        application = await verify_session.execute(
            "SELECT * FROM applications WHERE email = :email",
            {"email": f"john_{unique_id}@test.com"},
        )
        app_result = application.fetchone()
        assert app_result is not None

        # Check ticket exists
        ticket = await verify_session.execute(
            "SELECT * FROM tickets WHERE code = :code", {"code": ticket_code}
        )
        ticket_result = ticket.fetchone()
        assert ticket_result is not None


@pytest.mark.asyncio
async def test_ticket_status_tracking(client: AsyncClient):
    """Test ticket-based status tracking without authentication."""
    unique_id = str(uuid.uuid4())[:8]

    # Setup test data
    async with AsyncSessionLocal() as session:
        # Create company
        company = Company(
            name=f"Test Company {unique_id}",
            slug=f"test-company-{unique_id}",
            website="test.com",
            logo_url="https://test.com/logo.png",
        )
        session.add(company)
        await session.commit()

        # Create HR user
        user = User(
            email=f"hr_{unique_id}@test.com",
            password_hash=get_password_hash("password123"),
            full_name="HR Test",
            role=UserRole.HR,
            company_id=company.id,
        )
        session.add(user)
        await session.commit()

        # Create job
        job = Job(
            title="Software Engineer",
            department="Engineering",
            employment_type="FULL_TIME",
            status=JobStatus.PUBLISHED,
            location="Jakarta",
            apply_code=f"TEST{unique_id}",
            description="Test job description",
            company_id=company.id,
            created_by=user.id,
            is_public=True,
        )
        session.add(job)
        await session.commit()

        # Create form fields
        form_field = JobFormField(
            job_id=job.id,
            field_key="full_name",
            label="Full Name",
            field_type=FormFieldType.TEXT,
            is_required=True,
            order_index=1,
        )
        session.add(form_field)
        await session.commit()

        # Create applicant user
        from app.features.applications.models import Application
        from app.features.tickets.models import Ticket
        from app.shared.enums.application_status import ApplicationStatus
        from app.shared.enums.ticket_status import TicketStatus

        applicant = User(
            email=f"john_{unique_id}@test.com",
            full_name="John Doe",
            phone="081234567890",
            role=UserRole.APPLICANT,
        )
        session.add(applicant)
        await session.commit()

        # Create application with ticket
        application = Application(
            job_id=job.id,
            applicant_id=applicant.id,
            status=ApplicationStatus.APPLIED,
        )
        session.add(application)
        await session.commit()

        ticket = Ticket(
            application_id=application.id,
            code=f"TKT-2024-{unique_id}",
            status=TicketStatus.OPEN,
        )
        session.add(ticket)
        await session.commit()

        ticket_code = ticket.code

    # Test ticket tracking endpoint
    response = await client.get(f"/api/v1/tickets/track/{ticket_code}")

    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["ticket_code"] == ticket_code
    assert "status" in data["data"]


@pytest.mark.asyncio
async def test_duplicate_application_prevention(client: AsyncClient):
    """Test that duplicate applications are prevented."""
    unique_id = str(uuid.uuid4())[:8]

    # Setup test data
    async with AsyncSessionLocal() as session:
        # Create company
        company = Company(
            name=f"Test Company {unique_id}",
            slug=f"test-company-{unique_id}",
            website="test.com",
            logo_url="https://test.com/logo.png",
        )
        session.add(company)
        await session.commit()

        # Create HR user
        user = User(
            email=f"hr_{unique_id}@test.com",
            password_hash=get_password_hash("password123"),
            full_name="HR Test",
            role=UserRole.HR,
            company_id=company.id,
        )
        session.add(user)
        await session.commit()

        # Create job
        job = Job(
            title="Software Engineer",
            department="Engineering",
            employment_type="FULL_TIME",
            status=JobStatus.PUBLISHED,
            location="Jakarta",
            apply_code=f"TEST{unique_id}",
            description="Test job description",
            company_id=company.id,
            created_by=user.id,
            is_public=True,
        )
        session.add(job)
        await session.commit()

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
        await session.commit()

        job_id = job.id

    # First application
    application_data = {
        "job_id": job_id,
        "apply_code": f"TEST{unique_id}",
        "full_name": "John Doe",
        "email": f"john_{unique_id}@test.com",
    }

    response1 = await client.post(
        f"/api/v1/applications/public/jobs/{job_id}/apply", data=application_data
    )

    assert response1.status_code == 200

    # Second application with same email (should fail)
    response2 = await client.post(
        f"/api/v1/applications/public/jobs/{job_id}/apply", data=application_data
    )

    assert response2.status_code == 400  # Bad request due to duplicate
    data2 = response2.json()
    assert data2["success"] is False
    assert "duplicate" in data2["message"].lower()
