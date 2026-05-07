"""Integration tests for Audit Logs."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from app.shared.enums import EmploymentType

@pytest.mark.asyncio
async def test_hr_can_view_audit_logs_for_own_company(client: AsyncClient, hr_token: str, test_db_session):
    """HR harus bisa melihat log audit yang relevan dengan perusahaannya."""
    from app.features.jobs.models import Job
    from app.features.users.models import User
    
    # 1. Setup Job (aksi yang memicu audit log di service)
    payload = {
        "title": "Audit Test Job",
        "description": "Job for audit testing",
        "employment_type": EmploymentType.FULL_TIME.value
    }
    
    response = await client.post(
        "/api/v1/jobs/create-step1",
        json=payload,
        headers={"Authorization": f"Bearer {hr_token}"}
    )
    assert response.status_code == 200

    # 2. Get Audit Logs
    audit_response = await client.get(
        "/api/v1/audit-logs",
        headers={"Authorization": f"Bearer {hr_token}"}
    )
    
    assert audit_response.status_code == 200
    data = audit_response.json()
    logs = data["data"]["data"]
    assert len(logs) > 0
    actions = [log["action"] for log in logs]
    assert "JOB_CREATE" in actions
