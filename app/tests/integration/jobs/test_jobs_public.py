"""Integration tests for public jobs endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.hashing import get_password_hash
from app.features.companies.models import Company
from app.features.jobs.models import Job, JobFormField, JobKnockoutRule, JobRequirement
from app.features.users.models import User
from app.shared.enums.field_type import FormFieldType
from app.shared.enums.job_status import JobStatus
from app.shared.enums.user_roles import UserRole


@pytest.mark.asyncio
async def test_public_job_list(client: AsyncClient, db_session: AsyncSession):
    """Test public job listing endpoint."""
    # Setup test data
    company = Company(
        name="Test Company",
        domain="test.com",
        address="Test Address",
        logo_url="https://test.com/logo.png",
    )
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    user = User(
        email="hr@test.com",
        hashed_password=get_password_hash("password123"),
        full_name="HR Test",
        role=UserRole.HR,
        company_id=company.id,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Create a test job
    job = Job(
        title="Software Engineer",
        department="Engineering",
        employment_type="FULL_TIME",
        status=JobStatus.PUBLISHED,
        location="Jakarta",
        apply_code="TEST2024",
        description="Test job description",
        company_id=company.id,
        created_by=user.id,
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    # Test the endpoint
    response = await client.get("/api/v1/applications/public/jobs")
    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert len(data["data"]) >= 1  # Should have at least our test job
    assert data["data"][0]["title"] == "Software Engineer"
    assert data["data"][0]["department"] == "Engineering"


@pytest.mark.asyncio
async def test_public_job_detail(client: AsyncClient, db_session: AsyncSession):
    """Test public job detail endpoint."""
    # Setup test data
    company = Company(
        name="Test Company",
        domain="test.com",
        address="Test Address",
        logo_url="https://test.com/logo.png",
    )
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    user = User(
        email="hr@test.com",
        hashed_password=get_password_hash("password123"),
        full_name="HR Test",
        role=UserRole.HR,
        company_id=company.id,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Create a test job
    job = Job(
        title="Data Scientist",
        department="Data",
        employment_type="FULL_TIME",
        status=JobStatus.PUBLISHED,
        location="Bandung",
        apply_code="DATA2024",
        description="Test data science job",
        company_id=company.id,
        created_by=user.id,
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    # Add requirements
    requirement = JobRequirement(
        job_id=job.id, skill_name="Python", required=True, weight=40
    )
    db_session.add(requirement)

    # Add form fields
    form_field = JobFormField(
        job_id=job.id,
        field_key="experience_years",
        field_label="Years of Experience",
        field_type=FormFieldType.NUMBER,
        required=True,
        position=1,
    )
    db_session.add(form_field)

    # Add knockout rule
    knockout_rule = JobKnockoutRule(
        job_id=job.id,
        rule_type="experience",
        operator="gte",
        target_value="2",
        field_key="experience_years",
        action="auto_reject",
        rule_name="Minimum Experience",
    )
    db_session.add(knockout_rule)

    await db_session.commit()

    # Test the endpoint
    response = await client.get(f"/api/v1/applications/public/jobs/{job.id}")
    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert data["data"]["title"] == "Data Scientist"
    assert data["data"]["department"] == "Data"
    assert len(data["data"]["requirements"]) == 1
    assert len(data["data"]["form_fields"]) == 1
    assert len(data["data"]["knockout_rules"]) == 1
