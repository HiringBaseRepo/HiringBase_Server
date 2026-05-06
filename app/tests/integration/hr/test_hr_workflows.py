"""Integration tests for HR workflows including vacancy management and screening."""

import uuid

import pytest
from httpx import AsyncClient

from app.core.database.base import AsyncSessionLocal
from app.core.security.hashing import get_password_hash
from app.features.applications.models import Application, ApplicationAnswer
from app.features.companies.models import Company
from app.features.jobs.models import Job, JobFormField, JobKnockoutRule, JobRequirement
from app.features.users.models import User
from app.shared.enums.application_status import ApplicationStatus
from app.shared.enums.field_type import FormFieldType
from app.shared.enums.job_status import JobStatus
from app.shared.enums.user_roles import UserRole


@pytest.mark.asyncio
async def test_vacancy_lifecycle(client: AsyncClient, auth_headers):
    """Test complete vacancy lifecycle: creation, publishing, and knockout rule setup."""
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

        company_id = company.id
        user_id = user.id

    # Test job creation
    job_data = {
        "title": "Software Engineer",
        "department": "Engineering",
        "employment_type": "FULL_TIME",
        "location": "Jakarta",
        "description": "Test job description",
        "is_public": True,
    }

    response = await client.post("/api/v1/jobs/", json=job_data, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    job_id = data["data"]["id"]

    # Test job publishing
    publish_response = await client.post(
        f"/api/v1/jobs/{job_id}/publish", headers=auth_headers
    )

    assert publish_response.status_code == 200
    publish_data = publish_response.json()
    assert publish_data["success"] is True
    assert publish_data["data"]["status"] == JobStatus.PUBLISHED.value

    # Test knockout rule creation
    rule_data = {
        "rule_type": "experience",
        "field_key": "experience_years",
        "operator": "gte",
        "target_value": "2",
        "action": "auto_reject",
    }

    rule_response = await client.post(
        f"/api/v1/jobs/{job_id}/knockout-rules", json=rule_data, headers=auth_headers
    )

    assert rule_response.status_code == 200
    rule_data_response = rule_response.json()
    assert rule_data_response["success"] is True


@pytest.mark.asyncio
async def test_hr_screening_view(
    client: AsyncClient, auth_headers, mock_groq, mock_ocr_engine
):
    """Test HR viewing AI screening results for candidates."""
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

        # Create application
        application = Application(
            job_id=job.id,
            full_name="John Doe",
            email=f"john_{unique_id}@test.com",
            phone="081234567890",
            status=ApplicationStatus.AI_PROCESSING,
            company_id=company.id,
        )
        session.add(application)
        await session.commit()

        # Create application answers
        answers = [
            ApplicationAnswer(
                application_id=application.id,
                field_key="experience_years",
                value_text="3",
                value_number=3.0,
            ),
            ApplicationAnswer(
                application_id=application.id,
                field_key="education_level",
                value_text="s1",
            ),
        ]
        session.add_all(answers)
        await session.commit()

        job_id = job.id
        application_id = application.id

    # Test screening results endpoint
    response = await client.get(
        f"/api/v1/screening/applications/{application_id}", headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "scores" in data["data"]
    assert "status" in data["data"]


@pytest.mark.asyncio
async def test_tenant_isolation(client: AsyncClient, auth_headers):
    """Test that HR from Company A cannot access Company B's data."""
    unique_id = str(uuid.uuid4())[:8]

    # Setup Company A data
    async with AsyncSessionLocal() as session:
        # Create Company A
        company_a = Company(
            name=f"Company A {unique_id}",
            slug=f"company-a-{unique_id}",
            website="company-a.com",
            logo_url="https://company-a.com/logo.png",
        )
        session.add(company_a)
        await session.commit()

        # Create HR user for Company A
        user_a = User(
            email=f"hr_a_{unique_id}@test.com",
            password_hash=get_password_hash("password123"),
            full_name="HR Company A",
            role=UserRole.HR,
            company_id=company_a.id,
        )
        session.add(user_a)
        await session.commit()

        # Create Company B
        company_b = Company(
            name=f"Company B {unique_id}",
            slug=f"company-b-{unique_id}",
            website="company-b.com",
            logo_url="https://company-b.com/logo.png",
        )
        session.add(company_b)
        await session.commit()

        # Create job for Company B
        job_b = Job(
            title="Software Engineer",
            department="Engineering",
            employment_type="FULL_TIME",
            status=JobStatus.PUBLISHED,
            location="Jakarta",
            apply_code=f"TESTB{unique_id}",
            description="Test job for Company B",
            company_id=company_b.id,
            created_by=user_a.id,  # Created by Company A HR (edge case)
            is_public=True,
        )
        session.add(job_b)
        await session.commit()

        job_b_id = job_b.id

    # Try to access Company B's job with Company A HR credentials
    # (auth_headers is for Company A)
    response = await client.get(f"/api/v1/jobs/{job_b_id}", headers=auth_headers)

    # Should return 403 or 404 due to tenant isolation
    assert response.status_code in [403, 404]
    data = response.json()
    assert data["success"] is False


@pytest.mark.asyncio
async def test_interview_scheduling(client: AsyncClient, auth_headers):
    """Test interview scheduling workflow."""
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

        # Create application
        application = Application(
            job_id=job.id,
            full_name="John Doe",
            email=f"john_{unique_id}@test.com",
            phone="081234567890",
            status=ApplicationStatus.AI_PASSED,
            company_id=company.id,
        )
        session.add(application)
        await session.commit()

        job_id = job.id
        application_id = application.id

    # Test interview scheduling
    interview_data = {
        "application_id": application_id,
        "scheduled_at": "2024-12-31T10:00:00",
        "interviewer_id": "test-user-id",  # From auth_headers
        "notes": "Technical interview",
        "meeting_url": "https://zoom.us/test-meeting",
    }

    response = await client.post(
        "/api/v1/interviews/", json=interview_data, headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "id" in data["data"]
    assert data["data"]["application_id"] == application_id
