"""Integration tests for Job Form Builder."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from app.shared.enums import EmploymentType
from app.shared.enums.field_type import FormFieldType

@pytest.mark.asyncio
async def test_hr_can_manage_custom_job_form_fields(client: AsyncClient, hr_token: str, test_db_session):
    """HR harus bisa menambah, mengupdate, dan menghapus field kustom pada form lowongan."""
    from app.features.jobs.models import Job
    from app.features.users.models import User
    
    # Setup Job
    result = await test_db_session.execute(
        select(User).filter(User.email == "hr@test.com")
    )
    user = result.scalar_one()

    job = Job(
        title="Custom Form Job",
        description="Job with custom fields",
        company_id=user.company_id,
        employment_type=EmploymentType.FULL_TIME
    )
    test_db_session.add(job)
    await test_db_session.commit()

    # 1. Add Field
    response = await client.post(
        f"/api/v1/job-forms/{job.id}/fields?field_key=willing_to_travel&field_type=select&label=Bersedia+Traveling?&is_required=true",
        headers={"Authorization": f"Bearer {hr_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    field_id = data["data"]["field_id"]
    assert data["data"]["field_key"] == "willing_to_travel"

    # 2. Update Field
    update_payload = {"label": "Willing to travel overseas?"}
    update_response = await client.patch(
        f"/api/v1/job-forms/{job.id}/fields/{field_id}",
        json=update_payload,
        headers={"Authorization": f"Bearer {hr_token}"}
    )
    assert update_response.status_code == 200
    assert update_response.json()["data"]["updated"] is True

    # 3. Delete Field
    del_response = await client.delete(
        f"/api/v1/job-forms/{job.id}/fields/{field_id}",
        headers={"Authorization": f"Bearer {hr_token}"}
    )
    assert del_response.status_code == 200
    assert del_response.json()["data"]["deleted"] is True
