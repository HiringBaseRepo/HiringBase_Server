"""Integration tests for Scoring Templates."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from app.shared.enums import EmploymentType

@pytest.mark.asyncio
async def test_hr_can_create_and_update_scoring_template(client: AsyncClient, hr_token: str, test_db_session):
    """HR harus bisa membuat dan memperbarui template skor untuk lowongan."""
    from app.features.jobs.models import Job
    from app.features.users.models import User
    
    # 1. Get current user to link job to company
    result = await test_db_session.execute(
        select(User).filter(User.email == "hr@test.com")
    )
    user = result.scalar_one()

    job = Job(
        title="Software Engineer",
        description="Write code",
        company_id=user.company_id,
        employment_type=EmploymentType.FULL_TIME
    )
    test_db_session.add(job)
    await test_db_session.commit()

    # 2. Create Template
    response = await client.post(
        f"/api/v1/scoring/templates?job_id={job.id}&skill_match_weight=50&experience_weight=30&education_weight=20&portfolio_weight=0&soft_skill_weight=0&administrative_weight=0",
        headers={"Authorization": f"Bearer {hr_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    template_id = data["data"]["template_id"]
    assert data["data"]["job_id"] == job.id

    # 3. Update Template
    update_payload = {"skill_match_weight": 40, "portfolio_weight": 10}
    update_response = await client.patch(
        f"/api/v1/scoring/templates/{template_id}",
        json=update_payload,
        headers={"Authorization": f"Bearer {hr_token}"}
    )
    
    assert update_response.status_code == 200
    assert update_response.json()["data"]["updated"] is True

    # 4. Get Template
    get_response = await client.get(
        f"/api/v1/scoring/templates/{job.id}",
        headers={"Authorization": f"Bearer {hr_token}"}
    )
    assert get_response.status_code == 200
    assert get_response.json()["data"]["weights"]["skill_match"] == 40
