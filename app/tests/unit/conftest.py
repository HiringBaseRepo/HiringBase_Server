"""Local conftest for unit tests.

Override autouse fixtures from root conftest so that unit tests untuk
AI modules (OCR, document validator) bisa memanggil fungsi ASLI
tanpa diintersept oleh mock global.

Fixtures yang di-override:
- mock_ocr_engine → no-op (unit test mengatur sendiri via module patching)
- mock_groq → no-op (unit test mengatur sendiri via module patching)
- mock_get_session → no-op (unit test tidak butuh DB session)
- db_cleanup → no-op (unit test tidak butuh DB cleanup)
- override_db → no-op (unit test tidak butuh DB override)
- test_db_session → no-op (unit test tidak butuh DB)
"""

import pytest
import pytest_asyncio


@pytest.fixture(autouse=True)
def mock_ocr_engine():
    """Override: biarkan unit test OCR memanggil fungsi asli."""
    yield


@pytest.fixture(autouse=True)
def mock_groq():
    """Override: biarkan unit test validator memanggil fungsi asli."""
    yield


@pytest.fixture(autouse=True)
def mock_r2():
    """Override: unit test tidak butuh mock R2."""
    yield


@pytest_asyncio.fixture(autouse=True)
async def mock_get_session():
    """Override: unit test tidak butuh session mocking."""
    yield


@pytest_asyncio.fixture(autouse=True)
async def db_cleanup():
    """Override: unit test tidak butuh DB cleanup."""
    yield


@pytest.fixture(autouse=True)
def override_db():
    """Override: unit test tidak butuh DB override."""
    yield


@pytest_asyncio.fixture
async def test_db_session():
    """Override: unit test tidak butuh DB session."""
    yield None
