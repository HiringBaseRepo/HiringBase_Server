"""Unit tests for validator_step.run_document_semantic_check.

Menguji logika orchestrasi dokumen:
- OCR dipanggil untuk setiap dokumen KTP/Ijazah
- Hasil OCR dikirim ke LLM validator
- Flag dikembalikan jika dokumen tidak valid
- Dokumen non-KTP/IJAZAH dilewati
- OCR error tidak memblokir pipeline
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.shared.enums.document_type import DocumentType


# =============================================================================
# Helpers
# =============================================================================

def _make_doc(doc_type: DocumentType, url: str = "https://r2.example.com/doc.pdf"):
    doc = MagicMock()
    doc.document_type = doc_type
    doc.file_url = url
    return doc


def _make_applicant(name: str = "John Doe", email: str = "john@example.com"):
    applicant = MagicMock()
    applicant.full_name = name
    applicant.email = email
    return applicant


# =============================================================================
# Test: dokumen valid → tidak ada flag
# =============================================================================

@pytest.mark.asyncio
async def test_valid_documents_return_empty_flags():
    """Jika semua dokumen valid, hasilnya list kosong."""
    docs = [_make_doc(DocumentType.KTP), _make_doc(DocumentType.IJAZAH)]
    applicant = _make_applicant()

    with patch(
        "app.features.screening.services.validator_step.extract_text_from_document",
        AsyncMock(return_value="John Doe NIK 3273012345678901 berlaku seumur hidup"),
    ), patch(
        "app.features.screening.services.validator_step.validate_document_content",
        AsyncMock(return_value={"valid": True, "reason": "Dokumen valid", "confidence": 0.95}),
    ):
        from app.features.screening.services.validator_step import run_document_semantic_check
        flags = await run_document_semantic_check(docs, applicant)

    assert flags == []


# =============================================================================
# Test: dokumen invalid → flag ditambahkan
# =============================================================================

@pytest.mark.asyncio
async def test_invalid_ktp_adds_flag():
    """Jika KTP tidak valid, flag berisi peringatan KTP."""
    docs = [_make_doc(DocumentType.KTP)]
    applicant = _make_applicant(name="John Doe")

    with patch(
        "app.features.screening.services.validator_step.extract_text_from_document",
        AsyncMock(return_value="Ahmad Budi NIK 1234567890 berlaku seumur hidup"),
    ), patch(
        "app.features.screening.services.validator_step.validate_document_content",
        AsyncMock(return_value={
            "valid": False,
            "reason": "Nama pada KTP tidak cocok dengan data pelamar",
            "confidence": 0.9,
        }),
    ):
        from app.features.screening.services.validator_step import run_document_semantic_check
        flags = await run_document_semantic_check(docs, applicant)

    assert len(flags) == 1
    assert "KTP" in flags[0]
    assert "Nama pada KTP tidak cocok" in flags[0]


@pytest.mark.asyncio
async def test_invalid_ijazah_adds_flag():
    """Jika Ijazah tidak valid, flag berisi peringatan Ijazah."""
    docs = [_make_doc(DocumentType.IJAZAH)]
    applicant = _make_applicant()

    with patch(
        "app.features.screening.services.validator_step.extract_text_from_document",
        AsyncMock(return_value="Sertifikat Kompetensi - bukan ijazah"),
    ), patch(
        "app.features.screening.services.validator_step.validate_document_content",
        AsyncMock(return_value={
            "valid": False,
            "reason": "Dokumen bukan merupakan Ijazah",
            "confidence": 0.85,
        }),
    ):
        from app.features.screening.services.validator_step import run_document_semantic_check
        flags = await run_document_semantic_check(docs, applicant)

    assert len(flags) == 1
    assert "ijazah" in flags[0].lower()


@pytest.mark.asyncio
async def test_multiple_invalid_docs_each_add_flag():
    """Setiap dokumen yang invalid menambahkan flag tersendiri."""
    docs = [_make_doc(DocumentType.KTP), _make_doc(DocumentType.IJAZAH)]
    applicant = _make_applicant()

    with patch(
        "app.features.screening.services.validator_step.extract_text_from_document",
        AsyncMock(return_value="teks dokumen palsu"),
    ), patch(
        "app.features.screening.services.validator_step.validate_document_content",
        AsyncMock(return_value={
            "valid": False,
            "reason": "Dokumen terindikasi tidak autentik",
            "confidence": 0.8,
        }),
    ):
        from app.features.screening.services.validator_step import run_document_semantic_check
        flags = await run_document_semantic_check(docs, applicant)

    # Dua dokumen → dua flag
    assert len(flags) == 2


# =============================================================================
# Test: OCR dipanggil dengan URL yang benar
# =============================================================================

@pytest.mark.asyncio
async def test_ocr_called_with_document_url():
    """OCR harus dipanggil menggunakan URL dari dokumen."""
    doc_url = "https://r2.example.com/documents/ktp-abc123.pdf"
    docs = [_make_doc(DocumentType.KTP, url=doc_url)]
    applicant = _make_applicant()

    mock_ocr = AsyncMock(return_value="John Doe NIK 327301 berlaku seumur hidup")
    mock_validate = AsyncMock(return_value={"valid": True, "reason": "OK", "confidence": 0.99})

    with patch(
        "app.features.screening.services.validator_step.extract_text_from_document", mock_ocr
    ), patch(
        "app.features.screening.services.validator_step.validate_document_content", mock_validate
    ):
        from app.features.screening.services.validator_step import run_document_semantic_check
        await run_document_semantic_check(docs, applicant)

    mock_ocr.assert_called_once_with(doc_url)


# =============================================================================
# Test: LLM dipanggil dengan data yang benar
# =============================================================================

@pytest.mark.asyncio
async def test_validator_called_with_correct_applicant_data():
    """LLM validator harus menerima nama dan email pelamar yang benar."""
    docs = [_make_doc(DocumentType.KTP)]
    applicant = _make_applicant(name="Budi Santoso", email="budi@example.com")
    ocr_text = "Budi Santoso NIK 317201 Berlaku Seumur Hidup"

    mock_validate = AsyncMock(return_value={"valid": True, "reason": "OK", "confidence": 1.0})

    with patch(
        "app.features.screening.services.validator_step.extract_text_from_document",
        AsyncMock(return_value=ocr_text),
    ), patch(
        "app.features.screening.services.validator_step.validate_document_content", mock_validate
    ):
        from app.features.screening.services.validator_step import run_document_semantic_check
        await run_document_semantic_check(docs, applicant)

    # validator_step mengirim doc_type.value → enum value (lowercase)
    mock_validate.assert_called_once_with(
        "ktp",
        ocr_text,
        {"name": "Budi Santoso", "email": "budi@example.com"},
    )


# =============================================================================
# Test: Dokumen non-KTP/IJAZAH dilewati
# =============================================================================

@pytest.mark.asyncio
async def test_non_required_doc_types_are_skipped():
    """Dokumen selain KTP dan IJAZAH tidak diproses OCR/LLM."""
    # Gunakan tipe dokumen lain jika ada, atau buat mock yang tidak cocok
    other_doc = MagicMock()
    other_doc.document_type = MagicMock()
    # Buat agar dokumen ini tidak ada di [DocumentType.KTP, DocumentType.IJAZAH]
    other_doc.document_type.__eq__ = lambda self, other: False

    applicant = _make_applicant()

    mock_ocr = AsyncMock(return_value="")
    mock_validate = AsyncMock(return_value={"valid": True, "reason": "OK"})

    with patch(
        "app.features.screening.services.validator_step.extract_text_from_document", mock_ocr
    ), patch(
        "app.features.screening.services.validator_step.validate_document_content", mock_validate
    ):
        from app.features.screening.services.validator_step import run_document_semantic_check
        flags = await run_document_semantic_check([other_doc], applicant)

    # OCR dan LLM tidak dipanggil
    mock_ocr.assert_not_called()
    mock_validate.assert_not_called()
    assert flags == []


# =============================================================================
# Test: Daftar dokumen kosong
# =============================================================================

@pytest.mark.asyncio
async def test_empty_document_list_returns_empty_flags():
    """Jika tidak ada dokumen, hasilnya list kosong tanpa error."""
    applicant = _make_applicant()

    from app.features.screening.services.validator_step import run_document_semantic_check
    flags = await run_document_semantic_check([], applicant)

    assert flags == []
