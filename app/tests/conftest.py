"""Global test fixtures."""
import asyncio
import os
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
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
    from app.main import app
    from app.core.database.base import get_db
    
    async def _get_db_override():
        yield test_db_session
        
    app.dependency_overrides[get_db] = _get_db_override
    yield
    app.dependency_overrides.pop(get_db, None)

@pytest_asyncio.fixture
async def test_db_session():
    """Provide isolated database session for each test with a dedicated engine."""
    from app.core.database.base import create_engine_instance
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

    # Create a fresh engine for this test's loop
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
    
    # Create test company
    company = Company(
        name=f"Auth Company {unique_id}",
        slug=f"auth-company-{unique_id}",
    )
    test_db_session.add(company)
    await test_db_session.flush()
    await test_db_session.refresh(company)

    # Create test HR user
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
            "token_version": user.token_version
        }
    )
    
    return {
        "headers": {"Authorization": f"Bearer {access_token}"},
        "user": user,
        "company": company
    }

@pytest.fixture
def mock_unique_id():
    """Generate a unique ID for test isolation."""
    return str(uuid.uuid4())[:8]

@pytest.fixture
def mock_r2(monkeypatch):
    """Mock R2 storage operations."""
    class MockR2:
        def put_object(self, **kwargs): return {}
        def generate_presigned_url(self, **kwargs): return "https://mock-url.com/file"
        def delete_object(self, **kwargs): return {}
    
    mock = MockR2()
    monkeypatch.setattr("boto3.client", lambda *args, **kwargs: mock)
    return mock

@pytest.fixture
def mock_groq(monkeypatch):
    """Mock Groq LLM calls."""
    async def mock_call_llm(*args, **kwargs):
        return "Mocked AI explanation for candidate scoring."
    
    async def mock_validate_document(*args, **kwargs):
        return {"is_valid": True, "confidence": 0.95, "reason": "Document matches applicant data."}
    
    monkeypatch.setattr("app.ai.llm.client.call_llm", mock_call_llm)
    monkeypatch.setattr("app.ai.validator.document_validator.validate_document_content", mock_validate_document)

@pytest.fixture
def mock_ocr_engine(monkeypatch):
    """Mock OCR text extraction."""
    async def mock_extract(*args, **kwargs):
        return "Mocked extracted text from document for testing."
    
    monkeypatch.setattr("app.ai.ocr.engine.extract_text_from_document", mock_extract)
