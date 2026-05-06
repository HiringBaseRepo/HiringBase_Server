"""Integration tests for public jobs endpoints."""

import uuid
from datetime import datetime
import pytest
from httpx import AsyncClient
from app.features.companies.models import Company
from app.features.jobs.models import Job, JobFormField
from app.features.users.models import User
from app.shared.enums.employment_type import EmploymentType
from app.shared.enums.field_type import FormFieldType
from app.shared.enums.job_status import JobStatus
from app.shared.enums.user_roles import UserRole


@pytest.mark.asyncio
async def test_public_job_list(client: AsyncClient, test_db_session, override_db):
    """Test public job listing endpoint."""
    session = test_db_session
    unique_id = str(uuid.uuid4())[:8]
    
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
        title=f"Software Engineer {unique_id}",
        department="Engineering",
        employment_type=EmploymentType.FULL_TIME,
        status=JobStatus.PUBLISHED,
        location="Jakarta",
        apply_code=f"TEST{unique_id}",
        description="Test job description",
        company_id=company.id,
        created_by=user.id,
        is_public=True,
        published_at=datetime.utcnow(),
    )
    session.add(job)
    await session.flush()
    job_id = job.id

    # Test the endpoint
    response = await client.get(f"/api/v1/applications/public/jobs?q={unique_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    
    items = data["data"]["data"]
    assert len(items) >= 1
    found_job = next((j for j in items if j["id"] == job_id), None)
    assert found_job is not None


@pytest.mark.asyncio
async def test_public_job_detail(client: AsyncClient, test_db_session, override_db):
    """Test public job detail endpoint."""
    session = test_db_session
    unique_id = str(uuid.uuid4())[:8]
    
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
        title="Data Scientist",
        department="Data",
        employment_type=EmploymentType.FULL_TIME,
        status=JobStatus.PUBLISHED,
        location="Bandung",
        apply_code=f"DATA{unique_id}",
        description="Test data science job",
        company_id=company.id,
        created_by=user.id,
        is_public=True,
        published_at=datetime.utcnow(),
    )
    session.add(job)
    await session.flush()

    form_field = JobFormField(
        job_id=job.id,
        field_key="experience_years",
        label="Years of Experience",
        field_type=FormFieldType.NUMBER,
        is_required=True,
        order_index=1,
    )
    session.add(form_field)
    await session.flush()
    job_id = job.id

    # Test the endpoint
    response = await client.get(f"/api/v1/applications/public/jobs/{job_id}")
    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert data["data"]["title"] == "Data Scientist"
    assert data["data"]["form_fields"][0]["field_key"] == "experience_years"
