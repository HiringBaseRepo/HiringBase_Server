"""Document validation and OCR processing for screening service."""

from typing import Any

from app.ai.ocr.engine import extract_text_from_document
from app.ai.validator.document_validator import validate_document_content
from app.shared.enums.document_type import DocumentType


async def run_document_semantic_check(
    docs: list[Any],
    applicant: Any,
    force_fallback: bool = False,
) -> tuple[list[str], dict[str, str]]:
    """Run OCR and semantic validation on required documents.

    Args:
        docs: List of application documents
        applicant: Applicant object containing name and email
        force_fallback: If True, uses fallback logic on API failure instead of raising exception.

    Returns:
        Tuple of (List of validation flags, Dict of OCR results per doc type)
    """
    doc_validation_flags = []
    ocr_results = {}
    for doc in docs:
        if doc.document_type in [DocumentType.IDENTITY_CARD, DocumentType.DEGREE]:
            extracted_text = await extract_text_from_document(
                doc.file_url, force_fallback=force_fallback
            )
            ocr_results[doc.document_type.value] = extracted_text
            v_res = await validate_document_content(
                doc.document_type.value,
                extracted_text,
                {"name": applicant.full_name, "email": applicant.email},
                force_fallback=force_fallback,
            )
            if not v_res.get("valid"):
                doc_validation_flags.append(
                    f"Warning {doc.document_type.value}: {v_res.get('reason')}"
                )
    return doc_validation_flags, ocr_results
