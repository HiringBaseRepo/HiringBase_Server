"""Unit tests for document_validator.validate_document_content.

Menguji logika LLM-based document validator:
- No API key → fallback pass
- OCR text terlalu pendek → invalid langsung
- LLM response 200 + valid JSON → diparse
- LLM response error (non-200) → fallback pass
- Exception selama HTTP → fallback pass
- Prompt dibuat dengan data pelamar yang benar
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# =============================================================================
# Test: Tidak ada API Key → skip validasi, return valid=True
# =============================================================================

@pytest.mark.asyncio
async def test_validate_document_no_api_key_returns_valid():
    """Jika GROQ_API_KEY tidak dikonfigurasi, validator dilewati dan return valid=True."""
    with patch("app.ai.validator.document_validator.settings") as mock_settings:
        mock_settings.GROQ_API_KEY = None

        from app.ai.validator.document_validator import validate_document_content
        result = await validate_document_content(
            doc_type="KTP",
            ocr_text="Teks OCR normal",
            applicant_data={"name": "John Doe", "email": "john@example.com"},
        )

    assert result["valid"] is True
    assert "skip" in result["reason"].lower() or "no api" in result["reason"].lower()


# =============================================================================
# Test: OCR text terlalu pendek → invalid
# =============================================================================

@pytest.mark.asyncio
async def test_validate_document_short_ocr_text_returns_invalid():
    """Teks OCR < 10 karakter harus langsung return valid=False."""
    with patch("app.ai.validator.document_validator.settings") as mock_settings:
        mock_settings.GROQ_API_KEY = "test-key-xxx"

        from app.ai.validator.document_validator import validate_document_content
        result = await validate_document_content(
            doc_type="KTP",
            ocr_text="abc",  # terlalu pendek
            applicant_data={"name": "John Doe", "email": "john@example.com"},
        )

    assert result["valid"] is False
    assert result["confidence"] == 0.0
    assert "OCR" in result["reason"] or "pendek" in result["reason"]


@pytest.mark.asyncio
async def test_validate_document_empty_ocr_text_returns_invalid():
    """Teks OCR kosong harus langsung return valid=False."""
    with patch("app.ai.validator.document_validator.settings") as mock_settings:
        mock_settings.GROQ_API_KEY = "test-key-xxx"

        from app.ai.validator.document_validator import validate_document_content
        result = await validate_document_content(
            doc_type="IJAZAH",
            ocr_text="",
            applicant_data={"name": "Jane Doe", "email": "jane@example.com"},
        )

    assert result["valid"] is False
    assert result["confidence"] == 0.0


# =============================================================================
# Test: LLM API response 200 → parse JSON hasil validasi
# =============================================================================

@pytest.mark.asyncio
async def test_validate_document_parses_valid_llm_response():
    """LLM response 200 dengan JSON valid harus di-parse dan return hasilnya."""
    llm_response_body = {
        "choices": [
            {
                "message": {
                    "content": json.dumps({
                        "valid": True,
                        "reason": "Nama cocok dan format NIK valid",
                        "confidence": 0.97,
                    })
                }
            }
        ]
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = llm_response_body

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("app.ai.validator.document_validator.settings") as mock_settings, \
         patch("app.ai.validator.document_validator.httpx.AsyncClient", return_value=mock_client):

        mock_settings.GROQ_API_KEY = "test-key-xxx"
        mock_settings.GROQ_MODEL = "qwen/qwen3-32b"

        from app.ai.validator.document_validator import validate_document_content
        result = await validate_document_content(
            doc_type="KTP",
            ocr_text="John Doe NIK 3273012345678901 berlaku seumur hidup",
            applicant_data={"name": "John Doe", "email": "john@example.com"},
        )

    assert result["valid"] is True
    assert result["confidence"] == 0.97
    assert "NIK" in result["reason"]


@pytest.mark.asyncio
async def test_validate_document_parses_invalid_llm_response():
    """LLM response 200 dengan valid=False harus dikembalikan apa adanya."""
    llm_response_body = {
        "choices": [
            {
                "message": {
                    "content": json.dumps({
                        "valid": False,
                        "reason": "Nama pada KTP berbeda dengan data pelamar",
                        "confidence": 0.92,
                    })
                }
            }
        ]
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = llm_response_body

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("app.ai.validator.document_validator.settings") as mock_settings, \
         patch("app.ai.validator.document_validator.httpx.AsyncClient", return_value=mock_client):

        mock_settings.GROQ_API_KEY = "test-key-xxx"
        mock_settings.GROQ_MODEL = "qwen/qwen3-32b"

        from app.ai.validator.document_validator import validate_document_content
        result = await validate_document_content(
            doc_type="KTP",
            ocr_text="Ahmad Budi NIK 3273019876543210 berlaku seumur hidup",
            applicant_data={"name": "John Doe", "email": "john@example.com"},
        )

    assert result["valid"] is False
    assert result["confidence"] == 0.92


# =============================================================================
# Test: LLM API error (non-200) → fallback pass
# =============================================================================

@pytest.mark.asyncio
async def test_validate_document_api_error_returns_fallback_pass():
    """Jika LLM API error (status bukan 200), return fallback valid=True."""
    mock_response = MagicMock()
    mock_response.status_code = 503
    mock_response.text = "Service Unavailable"

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("app.ai.validator.document_validator.settings") as mock_settings, \
         patch("app.ai.validator.document_validator.httpx.AsyncClient", return_value=mock_client):

        mock_settings.GROQ_API_KEY = "test-key-xxx"
        mock_settings.GROQ_MODEL = "qwen/qwen3-32b"

        from app.ai.validator.document_validator import validate_document_content
        result = await validate_document_content(
            doc_type="KTP",
            ocr_text="John Doe NIK 3273012345678901 berlaku seumur hidup",
            applicant_data={"name": "John Doe", "email": "john@example.com"},
        )

    # Fallback: tidak memblokir pipeline
    assert result["valid"] is True
    assert result["confidence"] == 0.5


# =============================================================================
# Test: Exception HTTP → fallback pass, tidak crash
# =============================================================================

@pytest.mark.asyncio
async def test_validate_document_exception_returns_fallback_pass():
    """Jika terjadi exception saat HTTP call, return fallback valid=True tanpa crash."""
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(side_effect=Exception("Connection timeout"))

    with patch("app.ai.validator.document_validator.settings") as mock_settings, \
         patch("app.ai.validator.document_validator.httpx.AsyncClient", return_value=mock_client):

        mock_settings.GROQ_API_KEY = "test-key-xxx"
        mock_settings.GROQ_MODEL = "qwen/qwen3-32b"

        from app.ai.validator.document_validator import validate_document_content
        result = await validate_document_content(
            doc_type="IJAZAH",
            ocr_text="Universitas Indonesia Sarjana Informatika atas nama John Doe",
            applicant_data={"name": "John Doe", "email": "john@example.com"},
        )

    # Fallback: tidak memblokir pipeline, tidak crash
    assert result["valid"] is True


# =============================================================================
# Test: OCR engine — extract_text_from_document (pure unit)
# =============================================================================

@pytest.mark.asyncio
async def test_extract_text_from_document_returns_empty_on_download_error():
    """Jika download file gagal, extract_text_from_document harus return string kosong."""
    import httpx

    with patch("app.ai.ocr.engine._download_file", AsyncMock(side_effect=httpx.HTTPError("404 Not Found"))):
        from app.ai.ocr.engine import extract_text_from_document
        result = await extract_text_from_document("https://r2.example.com/missing.pdf")

    # Tidak boleh raise, harus return kosong
    assert isinstance(result, str)
    assert result == ""


@pytest.mark.asyncio
async def test_extract_text_from_document_pdf_calls_pdfplumber():
    """Untuk URL .pdf, harus memanggil PDF extractor."""
    pdf_content = b"%PDF-1.4 minimal fake pdf content"
    fake_text = "John Doe\nNIK 3273012345678901"

    with patch("app.ai.ocr.engine._download_file", AsyncMock(return_value=(pdf_content, "application/pdf"))), \
         patch("app.ai.ocr.engine._extract_text_pdf", return_value=fake_text):

        from app.ai.ocr.engine import extract_text_from_document
        result = await extract_text_from_document("https://r2.example.com/ktp.pdf")

    assert result == fake_text


@pytest.mark.asyncio
async def test_extract_text_from_document_image_calls_easyocr():
    """Untuk URL .jpg/.png, harus memanggil image OCR extractor."""
    image_content = b"\xff\xd8\xff fake jpeg bytes"
    fake_text = "Ahmad Budi\nNIK 123456"

    with patch("app.ai.ocr.engine._download_file", AsyncMock(return_value=(image_content, "image/jpeg"))), \
         patch("app.ai.ocr.engine._extract_text_image", return_value=fake_text):

        from app.ai.ocr.engine import extract_text_from_document
        result = await extract_text_from_document("https://r2.example.com/ktp.jpg")

    assert result == fake_text
