"""Integration tests for advanced auth security: Refresh Token Rotation & Reuse Detection."""

import uuid

import pytest
from httpx import AsyncClient

from app.core.security.hashing import get_password_hash
from app.features.companies.models import Company
from app.features.users.models import User
from app.shared.enums.user_roles import UserRole


@pytest.mark.asyncio
async def test_refresh_token_rotation(
    client: AsyncClient, test_db_session, override_db
):
    """Test that refresh tokens are properly rotated on each /refresh call."""
    session = test_db_session
    unique_id = str(uuid.uuid4())[:8]

    # Setup test data
    company = Company(
        name=f"Security Company {unique_id}",
        slug=f"security-company-{unique_id}",
    )
    session.add(company)
    await session.flush()

    # Create HR user with password hash
    user = User(
        email=f"hr_security_{unique_id}@test.com",
        full_name="HR Security Test",
        password_hash=get_password_hash("TestPassword123!"),
        role=UserRole.HR,
        company_id=company.id,
        is_active=True,
    )
    session.add(user)
    await session.flush()
    await session.refresh(user)

    initial_token_version = user.token_version

    # Step 1: Login HR to get initial refresh_token
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "TestPassword123!"},
    )
    assert login_response.status_code == 200
    login_data = login_response.json()
    assert login_data["success"] is True

    # Extract initial refresh_token from cookies
    initial_refresh_token = login_response.cookies.get("refresh_token")
    assert initial_refresh_token is not None, "Refresh token should be set in cookie"

    # Step 2: Rotate token (call /refresh with initial token)
    refresh_response_1 = await client.post(
        "/api/v1/auth/refresh",
        cookies={"refresh_token": initial_refresh_token},
    )
    assert refresh_response_1.status_code == 200

    # Extract rotated refresh_token
    rotated_refresh_token = refresh_response_1.cookies.get("refresh_token")
    assert rotated_refresh_token is not None
    assert rotated_refresh_token != initial_refresh_token, (
        "Token should be rotated (different value)"
    )

    # Step 3: Rotate again with the new token
    refresh_response_2 = await client.post(
        "/api/v1/auth/refresh",
        cookies={"refresh_token": rotated_refresh_token},
    )
    assert refresh_response_2.status_code == 200

    second_rotated_token = refresh_response_2.cookies.get("refresh_token")
    assert second_rotated_token is not None
    assert second_rotated_token != rotated_refresh_token, (
        "Token should be rotated again"
    )


@pytest.mark.asyncio
async def test_refresh_token_reuse_detection_kill_switch(
    client: AsyncClient, test_db_session, override_db
):
    """Test that reusing an old (already rotated) refresh token triggers Kill Switch.

    Security behavior:
    1. Login and rotate tokens once (old token should now be invalid)
    2. Attempt to use the OLD (already rotated) token
    3. System should detect reuse and:
       - Return 401 Unauthorized
       - Increment token_version in DB (Kill Switch)
       - Invalidate all refresh tokens for this user
    """
    session = test_db_session
    unique_id = str(uuid.uuid4())[:8]

    # Setup test data
    company = Company(
        name=f"KillSwitch Company {unique_id}",
        slug=f"killswitch-company-{unique_id}",
    )
    session.add(company)
    await session.flush()

    # Create HR user
    user = User(
        email=f"hr_killswitch_{unique_id}@test.com",
        full_name="HR KillSwitch Test",
        password_hash=get_password_hash("TestPassword123!"),
        role=UserRole.HR,
        company_id=company.id,
        is_active=True,
    )
    session.add(user)
    await session.flush()
    await session.refresh(user)

    initial_token_version = user.token_version

    # Step 1: Login to get initial refresh_token
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "TestPassword123!"},
    )
    assert login_response.status_code == 200

    old_refresh_token = login_response.cookies.get("refresh_token")
    assert old_refresh_token is not None

    # Step 2: Rotate token once (old token should be invalidated)
    refresh_response = await client.post(
        "/api/v1/auth/refresh",
        cookies={"refresh_token": old_refresh_token},
    )
    assert refresh_response.status_code == 200

    new_refresh_token = refresh_response.cookies.get("refresh_token")
    assert new_refresh_token is not None

    # Refresh DB session to get latest user state
    await session.refresh(user)
    token_version_after_rotation = user.token_version

    # Step 3: Attempt to reuse the OLD token (should fail with Kill Switch)
    reuse_attack_response = await client.post(
        "/api/v1/auth/refresh",
        cookies={"refresh_token": old_refresh_token},
    )

    # System should detect reuse and return 401
    assert reuse_attack_response.status_code == 401, (
        f"Expected 401 Unauthorized for reused token, got {reuse_attack_response.status_code}. "
        f"Response: {reuse_attack_response.text}"
    )

    reuse_data = reuse_attack_response.json()
    assert (
        "Security Alert" in reuse_data.get("detail", "")
        or "login" in reuse_data.get("detail", "").lower()
    )

    # Step 4: Verify Kill Switch was triggered (token_version incremented)
    await session.refresh(user)
    final_token_version = user.token_version

    assert final_token_version > token_version_after_rotation, (
        f"token_version should have been incremented after reuse detection. "
        f"Expected > {token_version_after_rotation}, got {final_token_version}"
    )

    # Step 5: Verify that NEW token is also now invalid (all sessions killed)
    final_refresh_attempt = await client.post(
        "/api/v1/auth/refresh",
        cookies={"refresh_token": new_refresh_token},
    )
    assert final_refresh_attempt.status_code == 401, (
        "Newly rotated token should also be invalid after Kill Switch"
    )


@pytest.mark.asyncio
async def test_concurrent_token_rotation_prevents_double_use(
    client: AsyncClient, test_db_session, override_db
):
    """Test that token rotation prevents double-use of the same token."""
    session = test_db_session
    unique_id = str(uuid.uuid4())[:8]

    # Setup test data
    company = Company(
        name=f"Concurrent Company {unique_id}",
        slug=f"concurrent-company-{unique_id}",
    )
    session.add(company)
    await session.flush()

    user = User(
        email=f"hr_concurrent_{unique_id}@test.com",
        full_name="HR Concurrent Test",
        password_hash=get_password_hash("TestPassword123!"),
        role=UserRole.HR,
        company_id=company.id,
        is_active=True,
    )
    session.add(user)
    await session.flush()

    # Login
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "TestPassword123!"},
    )
    assert login_response.status_code == 200

    shared_refresh_token = login_response.cookies.get("refresh_token")
    assert shared_refresh_token is not None

    # First rotation should succeed
    resp1 = await client.post(
        "/api/v1/auth/refresh",
        cookies={"refresh_token": shared_refresh_token},
    )
    assert resp1.status_code == 200

    # Second rotation attempt with SAME token should fail
    resp2 = await client.post(
        "/api/v1/auth/refresh",
        cookies={"refresh_token": shared_refresh_token},
    )
    assert resp2.status_code == 401, (
        "Same token used twice should be rejected on second attempt"
    )


@pytest.mark.asyncio
async def test_invalid_refresh_token_format_rejected(
    client: AsyncClient, test_db_session, override_db
):
    """Test that malformed refresh tokens are properly rejected."""
    # Test with completely invalid token
    invalid_response = await client.post(
        "/api/v1/auth/refresh",
        cookies={"refresh_token": "invalid.malformed.token"},
    )
    assert invalid_response.status_code == 401

    # Test with empty token
    empty_response = await client.post(
        "/api/v1/auth/refresh",
        cookies={"refresh_token": ""},
    )
    assert empty_response.status_code == 401

    # Test with missing cookie
    missing_response = await client.post("/api/v1/auth/refresh")
    assert missing_response.status_code == 401


@pytest.mark.asyncio
async def test_token_version_tracking_in_jwt(
    client: AsyncClient, test_db_session, override_db
):
    """Test that access tokens reflect the correct token_version and can be invalidated."""
    session = test_db_session
    unique_id = str(uuid.uuid4())[:8]

    # Setup test data
    company = Company(
        name=f"VersionTracking {unique_id}",
        slug=f"version-tracking-{unique_id}",
    )
    session.add(company)
    await session.flush()

    user = User(
        email=f"hr_version_{unique_id}@test.com",
        full_name="HR Version Track",
        password_hash=get_password_hash("TestPassword123!"),
        role=UserRole.HR,
        company_id=company.id,
        is_active=True,
    )
    session.add(user)
    await session.flush()

    # Login and get access token
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "TestPassword123!"},
    )
    assert login_response.status_code == 200
    login_data = login_response.json()

    initial_access_token = login_data["data"]["access_token"]
    initial_tv = user.token_version

    # Save old refresh token BEFORE any rotation
    old_refresh_token = login_response.cookies.get("refresh_token")
    assert old_refresh_token is not None

    # Call /me with initial access token (should succeed)
    me_response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {initial_access_token}"},
    )
    assert me_response.status_code == 200

    # Rotate token once (consumes old_refresh_token)
    refresh_response = await client.post(
        "/api/v1/auth/refresh",
        cookies={"refresh_token": old_refresh_token},
    )
    assert refresh_response.status_code == 200

    # Second attempt: reuse the ORIGINAL token (already rotated once)
    # This should trigger Kill Switch because old_refresh_token was already consumed
    reuse_attack_response = await client.post(
        "/api/v1/auth/refresh",
        cookies={"refresh_token": old_refresh_token},
    )
    assert reuse_attack_response.status_code == 401, (
        f"Reusing old rotated token should trigger Kill Switch. "
        f"Got {reuse_attack_response.status_code}: {reuse_attack_response.text}"
    )

    # Now old access token should be invalid (because token_version changed)
    invalid_me_response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {initial_access_token}"},
    )
    assert invalid_me_response.status_code == 401, (
        "Access token should be invalid after Kill Switch triggered"
    )
