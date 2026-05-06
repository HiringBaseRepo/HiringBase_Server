"""Global test fixtures."""
import asyncio
from contextlib import asynccontextmanager
import os
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from app.main import app
from app.core.config import settings

# Force testing environment
settings.APP_ENV = "testing"

@pytest_asyncio.fixture
async def client():
    """Create an async HTTP client for testing."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

@pytest.fixture(autouse=True)
def override_db(test_db_session):
    """Override get_db dependency to use the test session."""
    from app.core.database.base import get_db
    
    async def _get_db_override():
        yield test_db_session
        
    app.dependency_overrides[get_db] = _get_db_override
    yield
    app.dependency_overrides.pop(get_db, None)

@pytest_asyncio.fixture(autouse=True)
async def mock_get_session(monkeypatch, test_db_session):
    """Monkeypatch get_session used by process_screening background task.
    
    process_screening does: from app.core.database.session import get_session
    inside the function body (lazy import), so we patch BOTH:
    - the module-level name (if already imported at module load)
    - the source module to intercept lazy imports
    """
    @asynccontextmanager
    async def _mock_get_session():
        yield test_db_session

    # Patch source module so lazy `from ... import get_session` picks up mock
    monkeypatch.setattr("app.core.database.session.get_session", _mock_get_session)

    # Disable FastAPI BackgroundTasks so background jobs don't run in parallel
    from fastapi import BackgroundTasks
    monkeypatch.setattr(BackgroundTasks, "add_task", lambda *args, **kwargs: None)

    yield

@pytest_asyncio.fixture(autouse=True)
async def db_cleanup(test_db_session):
    """Truncate all tables before each test to ensure absolute isolation."""
    tables = [
        "audit_logs", "notifications", "interviews", "tickets",
        "candidate_scores", "application_status_logs", "application_documents",
        "application_answers", "applications", "job_knockout_rules",
        "job_form_fields", "job_scoring_templates", "job_requirements",
        "jobs", "refresh_tokens", "users", "companies"
    ]
    await test_db_session.execute(text(f"TRUNCATE {', '.join(tables)} CASCADE"))
    await test_db_session.commit()
    yield

@pytest_asyncio.fixture
async def test_db_session():
    """Provide isolated database session for each test with a dedicated engine."""
    from app.core.database.base import create_engine_instance
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

    test_engine = create_engine_instance()
    test_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async with test_session_factory() as session:
        yield session
        await session.rollback()
        await test_engine.dispose()

@pytest_asyncio.fixture
async def auth_headers(test_db_session):
    """Generate authentication headers for a real HR user using the shared test session."""
    from app.core.security.jwt import create_access_token
    from app.features.companies.models import Company
    from app.features.users.models import User
    from app.shared.enums import UserRole

    unique_id = str(uuid.uuid4())[:8]

    company = Company(
        name=f"Auth Company {unique_id}",
        slug=f"auth-company-{unique_id}",
    )
    test_db_session.add(company)
    await test_db_session.flush()
    await test_db_session.refresh(company)

    user = User(
        email=f"hr_{unique_id}@test.com",
        full_name="Auth HR User",
        role=UserRole.HR,
        company_id=company.id,
        is_active=True,
    )
    test_db_session.add(user)
    await test_db_session.flush()
    await test_db_session.refresh(user)

    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "role": user.role.value,
            "cid": user.company_id,
            "uid": user.id,
            "token_version": user.token_version,
        }
    )

    return {
        "headers": {"Authorization": f"Bearer {access_token}"},
        "user": user,
        "company": company,
    }

@pytest.fixture
def mock_unique_id():
    """Generate a unique ID for test isolation."""
    return str(uuid.uuid4())[:8]

@pytest.fixture(autouse=True)
def mock_r2(monkeypatch):
    """Mock R2/S3 storage (boto3) to prevent real network calls."""
    class MockS3Client:
        def put_object(self, **kwargs): return {}
        def generate_presigned_url(self, *args, **kwargs): return "https://mock-url.com/file"
        def delete_object(self, **kwargs): return {}
        def head_object(self, **kwargs): return {}

    mock = MockS3Client()
    monkeypatch.setattr("boto3.client", lambda *args, **kwargs: mock)
    return mock

@pytest.fixture(autouse=True)
def mock_ocr_engine(monkeypatch):
    """Mock OCR text extraction at the call site inside validator_step.
    
    validator_step.py does `from app.ai.ocr.engine import extract_text_from_document`
    at module level, so we must patch the name in THAT module's namespace.
    """
    async def mock_extract(*args, **kwargs):
        return "Mocked extracted text: Full Name, ID: 123456789, Valid: Seumur Hidup."

    # Patch where it is USED (import target in validator_step)
    monkeypatch.setattr(
        "app.features.screening.services.validator_step.extract_text_from_document",
        mock_extract,
    )
    # Also patch the source module for any other callers
    monkeypatch.setattr("app.ai.ocr.engine.extract_text_from_document", mock_extract)

@pytest.fixture(autouse=True)
def mock_groq(monkeypatch):
    """Mock Groq LLM calls at both the source and call sites."""
    async def mock_call_llm(*args, **kwargs):
        return "Mocked AI explanation for candidate scoring."

    async def mock_validate_document(*args, **kwargs):
        # Return 'valid' so document semantic check passes
        return {"valid": True, "confidence": 0.95, "reason": "Document matches applicant data."}

    # Source modules
    monkeypatch.setattr("app.ai.llm.client.call_llm", mock_call_llm)
    monkeypatch.setattr(
        "app.ai.validator.document_validator.validate_document_content",
        mock_validate_document,
    )
    # Call site in validator_step.py
    monkeypatch.setattr(
        "app.features.screening.services.validator_step.validate_document_content",
        mock_validate_document,
    )
