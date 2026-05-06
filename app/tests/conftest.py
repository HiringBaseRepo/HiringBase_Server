"""Global test fixtures and configuration."""

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.config.settings import settings
from app.main import app

# Force testing environment
settings.APP_ENV = "testing"


@pytest_asyncio.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def client():
    """Create an async HTTP client for testing."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
def mock_r2():
    """Mock Cloudflare R2 storage service."""
    mock_put_object = AsyncMock(return_value={"success": True})
    mock_get_presigned_url = AsyncMock(return_value="https://mock-r2-url.com/test.pdf")

    with (
        patch("boto3.client", return_value=MagicMock(put_object=mock_put_object)),
    ):
        yield {
            "put_object": mock_put_object,
            "get_presigned_url": mock_get_presigned_url,
        }


@pytest.fixture
def mock_groq():
    """Mock Groq LLM service."""
    mock_call_llm = AsyncMock(
        return_value="Mock LLM explanation generated successfully"
    )
    mock_validate_document = AsyncMock(
        return_value={
            "valid": True,
            "reason": "Document validation passed",
            "confidence": 0.95,
        }
    )

    with (
        patch("app.ai.llm.client.call_llm", mock_call_llm),
        patch(
            "app.ai.validator.document_validator.validate_document_content",
            mock_validate_document,
        ),
    ):
        yield {"call_llm": mock_call_llm, "validate_document": mock_validate_document}


@pytest.fixture
def mock_ocr_engine():
    """Mock OCR engine for document text extraction."""
    mock_extract_text = AsyncMock(return_value="Mock OCR extracted text from document")

    with patch("app.ai.ocr.engine.extract_text_from_document", mock_extract_text):
        yield {"extract_text": mock_extract_text}


@pytest.fixture
def mock_unique_id():
    """Generate unique IDs for test isolation."""
    return str(uuid.uuid4())[:8]


@pytest.fixture
async def test_db_session():
    """Provide isolated database session for each test."""
    from app.core.database.base import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        # Begin transaction
        await session.begin()
        yield session
        # Rollback transaction after test
        await session.rollback()


@pytest.fixture
async def auth_headers():
    """Generate authentication headers for HR user."""
    from app.core.security.jwt import create_access_token

    # Create a mock user
    user_data = {
        "user_id": "test-user-id",
        "email": "test@hr.com",
        "role": "hr",
        "company_id": "test-company-id",
    }

    token = create_access_token(user_data)
    return {"Authorization": f"Bearer {token}"}
