"""Semantic Document Validator using LLM (Groq)."""
import json
import httpx
import structlog
from typing import Dict, Any
from app.core.config import settings
from app.ai.llm.client import get_groq_api_keys, post_groq_chat_completion
from app.core.exceptions.custom_exceptions import AIAPIConnectionException, AIAPIServerException
from app.shared.helpers.localization import get_label

log = structlog.get_logger(__name__)

async def validate_document_content(
    doc_type: str,
    ocr_text: str,
    applicant_data: Dict[str, Any],
    force_fallback: bool = False
) -> Dict[str, Any]:
    """
    Validate document content (e.g., Identity Card, Degree) using Groq LLM.
    Compares OCR text with applicant profile data.
    
    Returns:
        Dict: { "valid": bool, "reason": str, "confidence": float }
    """
    if not get_groq_api_keys():
        log.warning("GROQ_API_KEY not configured, skipping semantic document validation")
        return {"valid": True, "reason": get_label("Validator skipped (no API key)"), "confidence": 1.0}
    
    if not ocr_text or len(ocr_text.strip()) < 10:
        return {
            "valid": False, 
            "reason": get_label("OCR text is too short or unreadable"), 
            "confidence": 0.0
        }

    # Prompt Engineering
    prompt = f"""
    Task: HR document validation (Hiring Assistant).
    Compare the OCR text from the {doc_type} document with the applicant's profile data.
    
    Applicant Data:
    - Full Name: {applicant_data.get('name')}
    - Email: {applicant_data.get('email')}
    
    OCR Text from {doc_type}:
    ---
    {ocr_text[:4000]}
    ---
    
    Instructions:
    1. Check if the Name in the document EXACTLY matches the Applicant Name. If different name found, set valid to false. No typos allowed.
    2. Verify if the document type being read is indeed a {doc_type}.
    3. Check the document's validity period (if any). Ensure it is still active or valid for life.
    4. Check for a valid document number format (e.g., ID number, Certificate number).
    5. Identify any signs that the document belongs to someone else, text manipulation, or anomalies.
    
    Response MUST be in JSON format only:
    {{
        "valid": boolean,
        "reason": "brief explanation in Indonesian",
        "confidence": float (0.0 to 1.0)
    }}
    """

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await post_groq_chat_completion(
                client=client,
                payload={
                    "model": settings.GROQ_MODEL,
                    "messages": [
                        {"role": "system", "content": "You are a professional HR document verifier. Output JSON only."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"}
                },
            )
            if resp is None:
                return {"valid": True, "reason": get_label("Validator skipped (no API key)"), "confidence": 1.0}
            
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                result = json.loads(content)
                log.info("Document validation result", doc_type=doc_type, valid=result.get("valid"))
                return result
            elif resp.status_code == 429:
                return {"valid": False, "reason": "API Limit (Groq). Silakan screening ulang beberapa saat lagi.", "confidence": 0.0}
            elif resp.status_code >= 500:
                if force_fallback:
                    return {"valid": False, "reason": "API Groq Error. Silakan coba screening ulang nanti.", "confidence": 0.0}
                raise AIAPIServerException(f"Groq API returned {resp.status_code}")
            else:
                log.error("Groq API error", status_code=resp.status_code, body=resp.text)
                return {"valid": False, "reason": "Gagal validasi (API Client Error). Silakan coba lagi.", "confidence": 0.0}
                
    except (httpx.TimeoutException, httpx.NetworkError) as exc:
        log.error("Document validation timeout/network error", error=str(exc))
        if force_fallback:
            return {"valid": False, "reason": "API Timeout. Silakan screening ulang nanti.", "confidence": 0.0}
        raise AIAPIConnectionException(str(exc))
    except Exception as exc:
        if isinstance(exc, (AIAPIConnectionException, AIAPIServerException)):
            raise exc
        log.error("Document validation exception", error=str(exc))
        return {"valid": False, "reason": "Sistem Gagal Validasi. Silakan screening ulang nanti.", "confidence": 0.0}
