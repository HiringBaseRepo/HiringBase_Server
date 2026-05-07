"""Unit tests for document_validator dan OCR engine internals.

Catatan arsitektur:
- conftest.py memiliki autouse fixture yang men-mock:
  * validate_document_content (di validator_step call site)
  * extract_text_from_document (di validator_step + source module)
- Test di sini menguji INTERNAL FUNCTIONS yang tidak terkena autouse mock:
  * validate_document_content (source module langsung, bukan via validator_step)
  * OCR helper functions: _extract_text_pdf, _extract_text_image, _download_file
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# =============================================================================
# Test: validate_document_content — logika internal (source module langsung)
# =============================================================================

@pytest.mark.asyncio
async def test_validate_document_no_api_key_returns_valid():
    """Jika GROQ_API_KEY tidak dikonfigurasi, validator dilewati dan return valid=True."""
    # Import dulu sebelum patch agar kita punya reference ke fungsi asli
    import importlib
    import app.ai.validator.document_validator as validator_module

    original_settings = validator_module.settings

    try:
        # Ganti settings langsung di module namespace
        mock_settings = MagicMock()
        mock_settings.GROQ_API_KEY = None
        validator_module.settings = mock_settings

        result = await validator_module.validate_document_content(
            doc_type="KTP",
            ocr_text="Teks OCR normal yang cukup panjang untuk lolos",
            applicant_data={"name": "John Doe", "email": "john@example.com"},
        )
    finally:
        validator_module.settings = original_settings  # restore

    assert result["valid"] is True
    # Localized check: "dilewati" (skipped) or "api key"
    reason = result["reason"].lower()
    assert "skip" in reason or "dilewati" in reason or "api key" in reason


@pytest.mark.asyncio
async def test_validate_document_short_ocr_text_returns_invalid():
    """Teks OCR < 10 karakter harus langsung return valid=False tanpa memanggil LLM."""
    import app.ai.validator.document_validator as validator_module

    original_settings = validator_module.settings
    try:
        mock_settings = MagicMock()
        mock_settings.GROQ_API_KEY = "test-key-xxx"
        validator_module.settings = mock_settings

        result = await validator_module.validate_document_content(
            doc_type="KTP",
            ocr_text="abc",  # < 10 karakter
            applicant_data={"name": "John Doe", "email": "john@example.com"},
        )
    finally:
        validator_module.settings = original_settings

    assert result["valid"] is False
    assert result["confidence"] == 0.0


@pytest.mark.asyncio
async def test_validate_document_empty_ocr_returns_invalid():
    """Teks OCR kosong harus langsung return valid=False."""
    import app.ai.validator.document_validator as validator_module

    original_settings = validator_module.settings
    try:
        mock_settings = MagicMock()
        mock_settings.GROQ_API_KEY = "test-key-xxx"
        validator_module.settings = mock_settings

        result = await validator_module.validate_document_content(
            doc_type="IJAZAH",
            ocr_text="",
            applicant_data={"name": "Jane Doe", "email": "jane@example.com"},
        )
    finally:
        validator_module.settings = original_settings

    assert result["valid"] is False
    assert result["confidence"] == 0.0


@pytest.mark.asyncio
async def test_validate_document_parses_valid_llm_response():
    """LLM response 200 dengan JSON valid harus di-parse dan return hasilnya."""
    import app.ai.validator.document_validator as validator_module

    llm_response_body = {
        "choices": [{
            "message": {
                "content": json.dumps({
                    "valid": True,
                    "reason": "Nama cocok dan format NIK valid",
                    "confidence": 0.97,
                })
            }
        }]
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = llm_response_body

    mock_http_client = AsyncMock()
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=False)
    mock_http_client.post = AsyncMock(return_value=mock_response)

    original_settings = validator_module.settings
    original_httpx = validator_module.httpx

    try:
        mock_settings = MagicMock()
        mock_settings.GROQ_API_KEY = "test-key-xxx"
        mock_settings.GROQ_MODEL = "qwen/qwen3-32b"
        validator_module.settings = mock_settings

        mock_httpx = MagicMock()
        mock_httpx.AsyncClient.return_value = mock_http_client
        validator_module.httpx = mock_httpx

        result = await validator_module.validate_document_content(
            doc_type="KTP",
            ocr_text="John Doe NIK 3273012345678901 berlaku seumur hidup",
            applicant_data={"name": "John Doe", "email": "john@example.com"},
        )
    finally:
        validator_module.settings = original_settings
        validator_module.httpx = original_httpx

    assert result["valid"] is True
    assert result["confidence"] == 0.97
    assert "NIK" in result["reason"]


@pytest.mark.asyncio
async def test_validate_document_parses_invalid_llm_response():
    """LLM response 200 dengan valid=False harus dikembalikan apa adanya."""
    import app.ai.validator.document_validator as validator_module

    llm_response_body = {
        "choices": [{
            "message": {
                "content": json.dumps({
                    "valid": False,
                    "reason": "Nama pada KTP berbeda dengan data pelamar",
                    "confidence": 0.92,
                })
            }
        }]
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = llm_response_body

    mock_http_client = AsyncMock()
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=False)
    mock_http_client.post = AsyncMock(return_value=mock_response)

    original_settings = validator_module.settings
    original_httpx = validator_module.httpx
    try:
        mock_settings = MagicMock()
        mock_settings.GROQ_API_KEY = "test-key-xxx"
        mock_settings.GROQ_MODEL = "qwen/qwen3-32b"
        validator_module.settings = mock_settings
        mock_httpx = MagicMock()
        mock_httpx.AsyncClient.return_value = mock_http_client
        validator_module.httpx = mock_httpx

        result = await validator_module.validate_document_content(
            doc_type="KTP",
            ocr_text="Ahmad Budi NIK 3273019876543210 berlaku seumur hidup",
            applicant_data={"name": "John Doe", "email": "john@example.com"},
        )
    finally:
        validator_module.settings = original_settings
        validator_module.httpx = original_httpx

    assert result["valid"] is False
    assert result["confidence"] == 0.92


@pytest.mark.asyncio
async def test_validate_document_api_error_returns_fallback_pass():
    """Jika LLM API error (status bukan 200), return fallback valid=True."""
    import app.ai.validator.document_validator as validator_module

    mock_response = MagicMock()
    mock_response.status_code = 503
    mock_response.text = "Service Unavailable"

    mock_http_client = AsyncMock()
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=False)
    mock_http_client.post = AsyncMock(return_value=mock_response)

    original_settings = validator_module.settings
    original_httpx = validator_module.httpx
    try:
        mock_settings = MagicMock()
        mock_settings.GROQ_API_KEY = "test-key-xxx"
        mock_settings.GROQ_MODEL = "qwen/qwen3-32b"
        validator_module.settings = mock_settings
        mock_httpx = MagicMock()
        mock_httpx.AsyncClient.return_value = mock_http_client
        validator_module.httpx = mock_httpx

        result = await validator_module.validate_document_content(
            doc_type="KTP",
            ocr_text="John Doe NIK 3273012345678901 berlaku seumur hidup",
            applicant_data={"name": "John Doe", "email": "john@example.com"},
        )
    finally:
        validator_module.settings = original_settings
        validator_module.httpx = original_httpx

    # Fallback: tidak memblokir pipeline
    assert result["valid"] is True
    assert result["confidence"] == 0.5


@pytest.mark.asyncio
async def test_validate_document_exception_returns_fallback():
    """Exception saat HTTP call harus return fallback valid=True tanpa crash."""
    import app.ai.validator.document_validator as validator_module

    mock_http_client = AsyncMock()
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=False)
    mock_http_client.post = AsyncMock(side_effect=Exception("Connection timeout"))

    original_settings = validator_module.settings
    original_httpx = validator_module.httpx
    try:
        mock_settings = MagicMock()
        mock_settings.GROQ_API_KEY = "test-key-xxx"
        mock_settings.GROQ_MODEL = "qwen/qwen3-32b"
        validator_module.settings = mock_settings
        mock_httpx = MagicMock()
        mock_httpx.AsyncClient.return_value = mock_http_client
        validator_module.httpx = mock_httpx

        result = await validator_module.validate_document_content(
            doc_type="IJAZAH",
            ocr_text="Universitas Indonesia Sarjana Informatika atas nama John Doe",
            applicant_data={"name": "John Doe", "email": "john@example.com"},
        )
    finally:
        validator_module.settings = original_settings
        validator_module.httpx = original_httpx

    assert result["valid"] is True


# =============================================================================
# Test: OCR engine helper functions (pure unit, tidak kena mock autouse)
# =============================================================================

@pytest.mark.asyncio
async def test_extract_text_from_document_empty_on_download_error():
    """Jika download file gagal, harus return string kosong tanpa crash."""
    import httpx
    import app.ai.ocr.engine as ocr_module

    # Patch _download_file langsung di source module
    original_dl = ocr_module._download_file
    try:
        async def _fail_download(url):
            raise httpx.HTTPError("Connection refused")

        ocr_module._download_file = _fail_download
        result = await ocr_module.extract_text_from_document("https://r2.example.com/missing.pdf")
    finally:
        ocr_module._download_file = original_dl

    assert isinstance(result, str)
    assert result == ""


@pytest.mark.asyncio
async def test_extract_text_from_document_pdf_calls_pdf_extractor():
    """Untuk content-type application/pdf, harus memanggil _extract_text_pdf."""
    import app.ai.ocr.engine as ocr_module

    fake_text = "John Doe\nNIK 3273012345678901"

    original_dl = ocr_module._download_file
    original_pdf = ocr_module._extract_text_pdf
    try:
        async def _mock_download(url):
            return b"%PDF-1.4 fake pdf", "application/pdf"

        ocr_module._download_file = _mock_download
        ocr_module._extract_text_pdf = lambda content: fake_text

        result = await ocr_module.extract_text_from_document("https://r2.example.com/ktp.pdf")
    finally:
        ocr_module._download_file = original_dl
        ocr_module._extract_text_pdf = original_pdf

    assert result == fake_text


@pytest.mark.asyncio
async def test_extract_text_from_document_image_calls_image_extractor():
    """Untuk content-type image/jpeg, harus memanggil _extract_text_image."""
    import app.ai.ocr.engine as ocr_module

    fake_text = "Ahmad Budi\nNIK 123456"

    original_dl = ocr_module._download_file
    original_img = ocr_module._extract_text_image
    try:
        async def _mock_download(url):
            return b"\xff\xd8\xff fake jpeg", "image/jpeg"

        ocr_module._download_file = _mock_download
        ocr_module._extract_text_image = lambda content: fake_text

        result = await ocr_module.extract_text_from_document("https://r2.example.com/ktp.jpg")
    finally:
        ocr_module._download_file = original_dl
        ocr_module._extract_text_image = original_img

    assert result == fake_text


# =============================================================================
# Test: _extract_text_pdf (pure sync, internal helper)
# =============================================================================

def test_extract_text_pdf_returns_empty_on_import_error():
    """Jika pdfplumber tidak terinstall, harus return string kosong."""
    import app.ai.ocr.engine as ocr_module
    import builtins

    original_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "pdfplumber":
            raise ImportError("pdfplumber not installed")
        return original_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=mock_import):
        result = ocr_module._extract_text_pdf(b"fake pdf content")

    assert result == ""


def test_is_image_detects_jpg_url():
    """Helper _is_image harus detect URL .jpg sebagai image."""
    from app.ai.ocr.engine import _is_image
    assert _is_image("https://r2.example.com/ktp.jpg", "application/octet-stream") is True


def test_is_image_detects_png_url():
    """Helper _is_image harus detect URL .png sebagai image."""
    from app.ai.ocr.engine import _is_image
    assert _is_image("https://r2.example.com/ktp.png", "") is True


def test_is_image_detects_image_content_type():
    """Helper _is_image harus detect content-type image/* sebagai image."""
    from app.ai.ocr.engine import _is_image
    assert _is_image("https://r2.example.com/doc", "image/jpeg") is True


def test_is_image_returns_false_for_pdf():
    """Helper _is_image harus return False untuk PDF."""
    from app.ai.ocr.engine import _is_image
    assert _is_image("https://r2.example.com/ijazah.pdf", "application/pdf") is False
