"""Integration tests for Auth flows (Login, Logout, Me, Registration)."""

import pytest
from httpx import AsyncClient
from app.shared.enums.user_roles import UserRole

@pytest.mark.asyncio
async def test_super_admin_can_register_hr(client: AsyncClient, super_admin_token: str, test_db_session):
    """Super Admin harus bisa mendaftarkan HR baru ke company yang sudah ada."""
    from app.features.companies.models import Company
    
    company = Company(name="Existing Co", slug="existing-co")
    test_db_session.add(company)
    await test_db_session.flush()
    
    payload = {
        "email": "new_hr@company.com",
        "full_name": "New HR Manager",
        "password": "Password123!",
        "company_id": company.id
    }
    
    response = await client.post(
        "/api/v1/users/hr",
        json=payload,
        headers={"Authorization": f"Bearer {super_admin_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["email"] == payload["email"]
    assert data["data"]["role"] == UserRole.HR.value

@pytest.mark.asyncio
async def test_hr_login_success_and_cookie_set(client: AsyncClient, test_db_session):
    """HR harus bisa login dan menerima refresh token di cookie."""
    from app.features.users.models import User
    from app.features.companies.models import Company
    from app.core.security.hashing import get_password_hash
    
    company = Company(name="Login Test Co", slug="login-test-co")
    test_db_session.add(company)
    await test_db_session.flush()
    
    hr_user = User(
        email="login_test@test.com",
        full_name="Login Tester",
        password_hash=get_password_hash("Secret123!"),
        role=UserRole.HR,
        company_id=company.id,
        is_active=True
    )
    test_db_session.add(hr_user)
    await test_db_session.commit()

    login_payload = {
        "email": "login_test@test.com",
        "password": "Secret123!"
    }
    response = await client.post("/api/v1/auth/login", json=login_payload)
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data["data"]
    assert "refresh_token" in client.cookies

@pytest.mark.asyncio
async def test_get_me_endpoint(client: AsyncClient, hr_token: str):
    """Endpoint /me harus mengembalikan detail user yang sedang login."""
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {hr_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["role"] == UserRole.HR.value
    assert "email" in data["data"]

@pytest.mark.asyncio
async def test_logout_clears_cookie(client: AsyncClient, hr_token: str):
    """Logout harus menghapus refresh token dari cookie."""
    client.cookies.set("refresh_token", "fake_token_to_be_deleted")
    # 3. Logout
    logout_response = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {hr_token}"}
    )
    assert logout_response.status_code == 200
    
    # Cek header Set-Cookie untuk memastikan instruksi penghapusan dikirim
    set_cookie = logout_response.headers.get("set-cookie", "")
    assert "refresh_token=;" in set_cookie or 'refresh_token=""' in set_cookie
    assert "Max-Age=0" in set_cookie or "expires=" in set_cookie
