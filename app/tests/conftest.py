"""Pytest fixtures for comprehensive testing."""

from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.database.base import Base, get_db
from app.main import app


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    """Create a fresh database session for each test."""
    # Create an in-memory SQLite database for testing
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=NullPool,
        connect_args={"check_same_thread": False},
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    TestingSessionLocal = sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )

    async with TestingSessionLocal() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()

    # Drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncClient:
    """Create an HTTP test client with mocked database session."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def mock_r2():
    """Mock Cloudflare R2 storage using moto."""
    with patch("boto3.client") as mock_boto_client:
        # Mock S3 client
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        # Mock put_object to return success
        mock_s3.put_object.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}

        # Mock get_object to return test content
        mock_s3.get_object.return_value = {
            "Body": MagicMock(),
            "ContentType": "application/pdf",
        }

        yield mock_s3


@pytest.fixture
def mock_groq():
    """Mock Groq LLM client."""
    with patch("app.ai.llm.client.call_llm") as mock_call_llm:
        # Return a test explanation
        mock_call_llm.return_value = "Test explanation for candidate profile"
        yield mock_call_llm


@pytest.fixture
def mock_document_validator():
    """Mock document validator."""
    with patch(
        "app.ai.validator.document_validator.validate_document_content"
    ) as mock_validate:
        # Return valid response
        mock_validate.return_value = {
            "valid": True,
            "reason": "Test validation passed",
            "confidence": 1.0,
        }
        yield mock_validate


@pytest.fixture
def mock_ocr_engine():
    """Mock OCR engine."""
    with patch("app.ai.ocr.engine.extract_text_from_document") as mock_extract:
        # Return test OCR text
        mock_extract.return_value = "Test OCR text extracted from document"
        yield mock_extract
