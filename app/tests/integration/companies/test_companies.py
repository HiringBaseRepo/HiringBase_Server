"""Integration tests for Company Management (Super Admin)."""

import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_super_admin_can_manage_companies(client: AsyncClient, super_admin_token: str, test_db_session):
    """Super Admin harus bisa membuat, list, suspend, dan activate company."""
    # 1. Create Company
    payload = {
        "name": "New Tenant Co",
        "slug": "new-tenant-co",
        "industry": "Technology"
    }
    response = await client.post(
        "/api/v1/companies",
        json=payload,
        headers={"Authorization": f"Bearer {super_admin_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    company_id = data["data"]["id"]
    assert data["data"]["name"] == "New Tenant Co"

    # 2. List Companies
    list_response = await client.get(
        "/api/v1/companies",
        headers={"Authorization": f"Bearer {super_admin_token}"}
    )
    assert list_response.status_code == 200
    assert any(c["name"] == "New Tenant Co" for c in list_response.json()["data"]["data"])

    # 3. Suspend Company
    suspend_response = await client.patch(
        f"/api/v1/companies/{company_id}/suspend",
        headers={"Authorization": f"Bearer {super_admin_token}"}
    )
    assert suspend_response.status_code == 200
    assert suspend_response.json()["data"]["is_suspended"] is True

    # 4. Activate Company
    activate_response = await client.patch(
        f"/api/v1/companies/{company_id}/activate",
        headers={"Authorization": f"Bearer {super_admin_token}"}
    )
    assert activate_response.status_code == 200
    assert activate_response.json()["data"]["is_suspended"] is False
