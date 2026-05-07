"""Integration tests for User Management (RBAC & Multi-tenancy)."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from app.features.users.models import User
from app.shared.enums.user_roles import UserRole

@pytest.mark.asyncio
async def test_hr_can_only_list_users_from_own_company(client: AsyncClient, hr_token: str, test_db_session):
    """HR hanya boleh melihat user dari perusahaannya sendiri."""
    from app.features.companies.models import Company
    
    # 1. Setup: Create another company and user
    other_comp = Company(name="Other Corp", slug="other-corp")
    test_db_session.add(other_comp)
    await test_db_session.flush()
    
    other_user = User(
        email="other@corp.com",
        full_name="Other User",
        password_hash="...",
        role=UserRole.HR,
        company_id=other_comp.id
    )
    test_db_session.add(other_user)
    await test_db_session.commit()

    # 2. Call List Users
    response = await client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {hr_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    # PaginatedResponse structure: data.data
    users = data["data"]["data"]
    
    # Pastikan other_user tidak ada di list
    emails = [u["email"] for u in users]
    assert "other@corp.com" not in emails
    # Pastikan hanya user dari company yang sama (HR Test Co dari fixture)
    assert all(u["email"] == "hr@test.com" or "other@corp.com" not in u["email"] for u in users)

@pytest.mark.asyncio
async def test_super_admin_can_list_all_users_or_filter_by_company(client: AsyncClient, super_admin_token: str, test_db_session):
    """Super Admin bisa melihat semua user atau filter per company."""
    from app.features.companies.models import Company
    
    # Setup 2 companies and users
    comp_a = Company(name="Company A", slug="comp-a")
    comp_b = Company(name="Company B", slug="comp-b")
    test_db_session.add_all([comp_a, comp_b])
    await test_db_session.flush()
    
    user_a = User(email="a@test.com", full_name="A", password_hash="...", role=UserRole.HR, company_id=comp_a.id)
    user_b = User(email="b@test.com", full_name="B", password_hash="...", role=UserRole.HR, company_id=comp_b.id)
    test_db_session.add_all([user_a, user_b])
    await test_db_session.commit()

    # 1. List All
    resp_all = await client.get("/api/v1/users", headers={"Authorization": f"Bearer {super_admin_token}"})
    assert len(resp_all.json()["data"]["data"]) >= 3 # superadmin + a + b

    # 2. Filter by Company A
    resp_a = await client.get(f"/api/v1/users?company_id={comp_a.id}", headers={"Authorization": f"Bearer {super_admin_token}"})
    users_a = resp_a.json()["data"]["data"]
    assert len(users_a) == 1
    assert users_a[0]["email"] == "a@test.com"
