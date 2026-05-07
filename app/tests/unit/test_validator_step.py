"""Unit tests for validator_step.run_document_semantic_check.

Tests document orchestration logic:
- OCR is called for each IDENTITY_CARD/DEGREE document
- OCR results are sent to the LLM validator
- Flags are returned if documents are invalid
- Non-IDENTITY_CARD/DEGREE documents are skipped
- OCR errors do not block the pipeline
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
# Test: valid documents → no flags
# =============================================================================

@pytest.mark.asyncio
async def test_valid_documents_return_empty_flags():
    """If all documents are valid, result is an empty list."""
    docs = [_make_doc(DocumentType.IDENTITY_CARD), _make_doc(DocumentType.DEGREE)]
    applicant = _make_applicant()

    with patch(
        "app.features.screening.services.validator_step.extract_text_from_document",
        AsyncMock(return_value="John Doe NIK 3273012345678901 valid for life"),
    ), patch(
        "app.features.screening.services.validator_step.validate_document_content",
        AsyncMock(return_value={"valid": True, "reason": "Document valid", "confidence": 0.95}),
    ):
        from app.features.screening.services.validator_step import run_document_semantic_check
        flags = await run_document_semantic_check(docs, applicant)

    assert flags == []


# =============================================================================
# Test: invalid document → flag added
# =============================================================================

@pytest.mark.asyncio
async def test_invalid_identity_card_adds_flag():
    """If IDENTITY_CARD is invalid, flag contains identity_card warning."""
    docs = [_make_doc(DocumentType.IDENTITY_CARD)]
    applicant = _make_applicant(name="John Doe")

    with patch(
        "app.features.screening.services.validator_step.extract_text_from_document",
        AsyncMock(return_value="Ahmad Budi NIK 1234567890 valid for life"),
    ), patch(
        "app.features.screening.services.validator_step.validate_document_content",
        AsyncMock(return_value={
            "valid": False,
            "reason": "Name on card does not match applicant data",
            "confidence": 0.9,
        }),
    ):
        from app.features.screening.services.validator_step import run_document_semantic_check
        flags = await run_document_semantic_check(docs, applicant)

    assert len(flags) == 1
    assert "identity_card" in flags[0].lower()
    assert "Name on card does not match" in flags[0]


@pytest.mark.asyncio
async def test_invalid_degree_adds_flag():
    """If DEGREE is invalid, flag contains degree warning."""
    docs = [_make_doc(DocumentType.DEGREE)]
    applicant = _make_applicant()

    with patch(
        "app.features.screening.services.validator_step.extract_text_from_document",
        AsyncMock(return_value="Competency Certificate - not a degree"),
    ), patch(
        "app.features.screening.services.validator_step.validate_document_content",
        AsyncMock(return_value={
            "valid": False,
            "reason": "Document is not a degree",
            "confidence": 0.85,
        }),
    ):
        from app.features.screening.services.validator_step import run_document_semantic_check
        flags = await run_document_semantic_check(docs, applicant)

    assert len(flags) == 1
    assert "degree" in flags[0].lower()


@pytest.mark.asyncio
async def test_multiple_invalid_docs_each_add_flag():
    """Each invalid document adds its own flag."""
    docs = [_make_doc(DocumentType.IDENTITY_CARD), _make_doc(DocumentType.DEGREE)]
    applicant = _make_applicant()

    with patch(
        "app.features.screening.services.validator_step.extract_text_from_document",
        AsyncMock(return_value="fake document text"),
    ), patch(
        "app.features.screening.services.validator_step.validate_document_content",
        AsyncMock(return_value={
            "valid": False,
            "reason": "Document indicates non-authentic content",
            "confidence": 0.8,
        }),
    ):
        from app.features.screening.services.validator_step import run_document_semantic_check
        flags = await run_document_semantic_check(docs, applicant)

    # Two documents → two flags
    assert len(flags) == 2


# =============================================================================
# Test: OCR called with correct URL
# =============================================================================

@pytest.mark.asyncio
async def test_ocr_called_with_document_url():
    """OCR must be called using the document's URL."""
    doc_url = "https://r2.example.com/documents/identity-abc123.pdf"
    docs = [_make_doc(DocumentType.IDENTITY_CARD, url=doc_url)]
    applicant = _make_applicant()

    mock_ocr = AsyncMock(return_value="John Doe NIK 327301 valid for life")
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
# Test: LLM called with correct data
# =============================================================================

@pytest.mark.asyncio
async def test_validator_called_with_correct_applicant_data():
    """LLM validator must receive the correct applicant name and email."""
    docs = [_make_doc(DocumentType.IDENTITY_CARD)]
    applicant = _make_applicant(name="John Doe", email="john@example.com")
    ocr_text = "John Doe NIK 317201 Valid for life"

    mock_validate = AsyncMock(return_value={"valid": True, "reason": "OK", "confidence": 1.0})

    with patch(
        "app.features.screening.services.validator_step.extract_text_from_document",
        AsyncMock(return_value=ocr_text),
    ), patch(
        "app.features.screening.services.validator_step.validate_document_content", mock_validate
    ):
        from app.features.screening.services.validator_step import run_document_semantic_check
        await run_document_semantic_check(docs, applicant)

    # validator_step sends doc_type.value → enum value (lowercase)
    mock_validate.assert_called_once_with(
        "identity_card",
        ocr_text,
        {"name": "John Doe", "email": "john@example.com"},
    )


# =============================================================================
# Test: Non-IDENTITY_CARD/DEGREE documents are skipped
# =============================================================================

@pytest.mark.asyncio
async def test_non_required_doc_types_are_skipped():
    """Documents other than IDENTITY_CARD and DEGREE are not processed by OCR/LLM."""
    other_doc = MagicMock()
    other_doc.document_type = DocumentType.OTHERS

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

    # OCR and LLM are not called
    mock_ocr.assert_not_called()
    mock_validate.assert_not_called()
    assert flags == []


# =============================================================================
# Test: Empty document list
# =============================================================================

@pytest.mark.asyncio
async def test_empty_document_list_returns_empty_flags():
    """If no documents are provided, result is an empty list without error."""
    applicant = _make_applicant()

    from app.features.screening.services.validator_step import run_document_semantic_check
    flags = await run_document_semantic_check([], applicant)

    assert flags == []
