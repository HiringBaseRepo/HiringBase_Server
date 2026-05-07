"""OCR engine using Mistral Document AI API."""
from __future__ import annotations

import httpx
import structlog
from app.core.config import settings
from app.core.exceptions.custom_exceptions import AIAPIConnectionException, AIAPIServerException, AIAPIException

log = structlog.get_logger(__name__)

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".avif"}


def _is_image(url: str) -> bool:
    """Detect if URL points to an image based on extension."""
    url_lower = url.lower().split("?")[0]
    return any(url_lower.endswith(ext) for ext in _IMAGE_EXTS)


async def extract_text_from_document(file_url: str, force_fallback: bool = False) -> str:
    """Extract text from document URL (PDF or image) using Mistral OCR API.

    Flow:
    1. Detect document type (document_url for PDF, image_url for Images)
    2. Call Mistral OCR API v1
    3. Concatenate markdown results from all pages
    4. Fallback: return empty string

    Args:
        file_url: Public file URL on Cloudflare R2
        force_fallback: If True, returns empty string on transient API failure instead of raising.

    Returns:
        Extracted text in markdown format, or empty string if failed
    """
    if not settings.MISTRAL_API_KEY:
        log.warning("MISTRAL_API_KEY not configured, OCR skipped")
        return ""

    is_img = _is_image(file_url)
    doc_type = "image_url" if is_img else "document_url"
    
    payload = {
        "model": settings.MISTRAL_MODEL,
        "document": {
            "type": doc_type,
            doc_type: file_url
        }
    }

    try:
        log.info("Requesting Mistral OCR", url=file_url, type=doc_type)
        
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(
                "https://api.mistral.ai/v1/ocr",
                headers={
                    "Authorization": f"Bearer {settings.MISTRAL_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            
            if resp.status_code == 200:
                data = resp.json()
                pages = data.get("pages", [])
                full_text = "\n\n".join(
                    [page.get("markdown", "") for page in pages if page.get("markdown")]
                )
                if full_text:
                    log.info("OCR extraction successful via Mistral", pages=len(pages), chars=len(full_text))
                    return full_text.strip()
                return ""
            
            elif resp.status_code >= 500:
                if not force_fallback:
                    raise AIAPIServerException(f"Mistral OCR returned {resp.status_code}")
                log.error("Mistral OCR API 5xx, force fallback", status_code=resp.status_code)
                return ""
            else:
                log.error("Mistral OCR API error", status_code=resp.status_code, body=resp.text)
                return ""

    except (httpx.TimeoutException, httpx.NetworkError) as exc:
        log.error("Mistral OCR timeout/network error", url=file_url)
        if not force_fallback:
            raise AIAPIConnectionException(str(exc))
        return ""
    except Exception as exc:
        if isinstance(exc, AIAPIException):
            raise exc
        log.error("Mistral OCR unexpected error", error=str(exc), url=file_url)
        return ""
