"""Application flow integration tests."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.core.database.base import get_db, AsyncSessionLocal
from app.features.models import Job, Company, User, JobFormField
from app.shared.enums.job_status import JobStatus
from app.shared.enums.field_type import FormFieldType
from app.shared.enums.user_roles import UserRole
from app.core.security.hashing import get_password_hash


@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


async def test_public_job_list(client: AsyncClient):
    response = await client.get("/api/v1/applications/public/jobs")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
