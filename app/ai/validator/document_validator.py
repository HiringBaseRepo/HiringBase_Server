"""Semantic Document Validator using LLM (Groq)."""

import json
import html
from typing import Any, Dict

import httpx
import structlog

from app.ai.llm.client import get_groq_api_keys, post_groq_chat_completion
from app.core.config import settings
from app.core.exceptions.custom_exceptions import (
    AIAPIConnectionException,
    AIAPIServerException,
)
from app.shared.helpers.localization import get_label

log = structlog.get_logger(__name__)


async def validate_document_content(
    doc_type: str,
    ocr_text: str,
    applicant_data: Dict[str, Any],
    force_fallback: bool = False,
) -> Dict[str, Any]:
    """
    Validate document content (e.g., Identity Card, Degree) using Groq LLM.
    Compares OCR text with applicant profile data.

    Returns:
        Dict with validation result, confidence, and machine-readable checks.
    """
    if not get_groq_api_keys():
        log.warning("GROQ_API_KEY not configured, skipping semantic document validation")
        return _normalize_document_validation_result(
            {
                "valid": True,
                "reason": get_label("Validator skipped (no API key)"),
                "confidence": 1.0,
            }
        )

    if not ocr_text or len(ocr_text.strip()) < 10:
        if force_fallback:
            return _normalize_document_validation_result(
                {
                    "valid": True,
                    "reason": get_label("OCR text too short (fallback mode — accepting on best effort)"),
                    "confidence": 0.5,
                }
            )
        return _normalize_document_validation_result(
            {
                "valid": False,
                "reason": get_label("OCR text is too short or unreadable"),
                "confidence": 0.0,
            }
        )

    # Clean OCR text from HTML/XML entities (e.g., &amp; -> &)
    cleaned_ocr = html.unescape(ocr_text)

    prompt = f"""
    Task: HR document validation (Hiring Assistant).
    Compare the OCR text from the {doc_type} document with the applicant's profile data.

    Applicant Data:
    - Full Name: {applicant_data.get('name')}
    - Email: {applicant_data.get('email')}

    OCR Text from {doc_type}:
    ---
    {cleaned_ocr[:4000]}
    ---

    Instructions:
    1. Check if the Name in the document matches the Applicant Name. The matching should be CASE-INSENSITIVE (e.g., "ABDEL MUWAFFAQ NOURI" matches "Abdel Muwaffaq Nouri"). Do not flag it as a mismatch just because of all-caps vs title-case. Also allow minor formatting/title differences (like academic titles "S.Kom.", "M.T.", etc.).
       CRITICAL: Ignore minor OCR typos, character/scanning artifacts (for example, if the letter 'Q' is scanned as '&' or '&amp;', or there's a missing/extra character, but the rest of the name matches). If it is clearly the same person with a slight OCR scanning error, set "name_match" to true in checks and "valid" to true, explaining the minor OCR noise in the "reason". Only set "valid" or "name_match" to false if it is a completely different person's name (e.g., "JUJANTI JIMAMORA" vs "Isa").
    2. Verify if the document type being read is indeed a {doc_type}.
    3. Check the document's validity period (if any). Ensure it is still active or valid for life.
    4. Check for a valid document number format (e.g., ID number, Certificate number).
    5. Identify any signs that the document belongs to someone else, text manipulation, or anomalies.

    Response MUST be in JSON format only:
    {{
        "valid": boolean,
        "reason": "brief explanation in Indonesian",
        "confidence": float (0.0 to 1.0),
        "checks": {{
            "name_match": boolean,
            "document_type_match": boolean,
            "valid_period": boolean | null
        }}
    }}
    """

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await post_groq_chat_completion(
                client=client,
                payload={
                    "model": settings.GROQ_MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a professional HR document verifier. Output JSON only.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"},
                },
            )
            if resp is None:
                return _normalize_document_validation_result(
                    {
                        "valid": True,
                        "reason": get_label("Validator skipped (no API key)"),
                        "confidence": 1.0,
                    }
                )

            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                result = _normalize_document_validation_result(json.loads(content))
                log.info(
                    "Document validation result",
                    doc_type=doc_type,
                    valid=result.get("valid"),
                    checks=result.get("checks"),
                )
                return result
            if resp.status_code == 429:
                return _normalize_document_validation_result(
                    {
                        "valid": False,
                        "reason": "API Limit (Groq). Silakan screening ulang beberapa saat lagi.",
                        "confidence": 0.0,
                    }
                )
            if resp.status_code >= 500:
                if force_fallback:
                    return _normalize_document_validation_result(
                        {
                            "valid": False,
                            "reason": "API Groq Error. Silakan coba screening ulang nanti.",
                            "confidence": 0.0,
                        }
                    )
                raise AIAPIServerException(f"Groq API returned {resp.status_code}")

            log.error("Groq API error", status_code=resp.status_code, body=resp.text)
            return _normalize_document_validation_result(
                {
                    "valid": False,
                    "reason": "Gagal validasi (API Client Error). Silakan coba lagi.",
                    "confidence": 0.0,
                }
            )

    except (httpx.TimeoutException, httpx.NetworkError) as exc:
        log.error("Document validation timeout/network error", error=str(exc))
        if force_fallback:
            return _normalize_document_validation_result(
                {
                    "valid": False,
                    "reason": "API Timeout. Silakan screening ulang nanti.",
                    "confidence": 0.0,
                }
            )
        raise AIAPIConnectionException(str(exc))
    except Exception as exc:
        if isinstance(exc, (AIAPIConnectionException, AIAPIServerException)):
            raise exc
        log.error("Document validation exception", error=str(exc))
        return _normalize_document_validation_result(
            {
                "valid": False,
                "reason": "Sistem Gagal Validasi. Silakan screening ulang nanti.",
                "confidence": 0.0,
            }
        )


def _normalize_document_validation_result(result: Dict[str, Any]) -> Dict[str, Any]:
    checks = result.get("checks")
    if not isinstance(checks, dict):
        checks = {}

    return {
        "valid": bool(result.get("valid", False)),
        "reason": str(result.get("reason", "")).strip(),
        "confidence": float(result.get("confidence", 0.0) or 0.0),
        "checks": {
            "name_match": _coerce_optional_bool(checks.get("name_match")),
            "document_type_match": _coerce_optional_bool(checks.get("document_type_match")),
            "valid_period": _coerce_optional_bool(checks.get("valid_period")),
        },
    }


def _coerce_optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "yes", "1"}:
            return True
        if normalized in {"false", "no", "0"}:
            return False
    return None
