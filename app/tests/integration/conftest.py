"""Fixtures for Auth and User integration tests."""

import pytest_asyncio
from app.core.security.jwt import create_access_token
from app.features.users.models import User
from app.features.companies.models import Company
from app.shared.enums import UserRole

@pytest_asyncio.fixture
async def super_admin_token(test_db_session):
    """Generate token for a Super Admin."""
    user = User(
        email="superadmin@test.com",
        full_name="Super Admin",
        role=UserRole.SUPER_ADMIN,
        is_active=True,
    )
    test_db_session.add(user)
    await test_db_session.flush()
    await test_db_session.refresh(user)

    token = create_access_token(
        data={
            "sub": str(user.id),
            "role": user.role.value,
            "uid": user.id,
            "token_version": user.token_version,
        }
    )
    return token

@pytest_asyncio.fixture
async def hr_token(test_db_session):
    """Generate token for an HR user."""
    company = Company(name="HR Test Co", slug="hr-test-co")
    test_db_session.add(company)
    await test_db_session.flush()
    
    user = User(
        email="hr@test.com",
        full_name="HR User",
        role=UserRole.HR,
        company_id=company.id,
        is_active=True,
    )
    test_db_session.add(user)
    await test_db_session.flush()
    await test_db_session.refresh(user)

    token = create_access_token(
        data={
            "sub": str(user.id),
            "role": user.role.value,
            "cid": user.company_id,
            "uid": user.id,
            "token_version": user.token_version,
        }
    )
    return token
