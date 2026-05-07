"""Integration tests for Notifications."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from app.shared.enums.notification_type import NotificationType

@pytest.mark.asyncio
async def test_hr_can_manage_notifications(client: AsyncClient, hr_token: str, test_db_session):
    """HR harus bisa melihat dan menandai notifikasi sebagai terbaca."""
    from app.features.notifications.models import Notification
    from app.features.users.models import User
    
    # 1. Setup Notification
    result = await test_db_session.execute(
        select(User).filter(User.email == "hr@test.com")
    )
    user = result.scalar_one()
    
    notification = Notification(
        user_id=user.id,
        type=NotificationType.APPLY_CONFIRMED,
        title="New Application",
        message="John Doe applied for SE role",
        is_read=False
    )
    test_db_session.add(notification)
    await test_db_session.commit()

    # 2. List Notifications
    response = await client.get(
        "/api/v1/notifications?unread_only=true",
        headers={"Authorization": f"Bearer {hr_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]["data"]) == 1
    notification_id = data["data"]["data"][0]["id"]

    # 3. Mark Read
    read_response = await client.post(
        f"/api/v1/notifications/{notification_id}/read",
        headers={"Authorization": f"Bearer {hr_token}"}
    )
    assert read_response.status_code == 200
    # Schema NotificationReadResponse menggunakan 'read'
    assert read_response.json()["data"]["read"] is True

    # 4. Verify Unread is 0
    list_unread = await client.get(
        "/api/v1/notifications?unread_only=true",
        headers={"Authorization": f"Bearer {hr_token}"}
    )
    assert len(list_unread.json()["data"]["data"]) == 0
