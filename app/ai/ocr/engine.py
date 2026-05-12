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


from app.core.cache.service import cache_service

async def extract_text_from_document(file_url: str, force_fallback: bool = False) -> str:
    """Extract text from document URL (PDF or image) using Mistral OCR API with Redis caching.

    Flow:
    1. Check Redis cache first
    2. Detect document type (document_url for PDF, image_url for Images)
    3. Call Mistral OCR API v1
    4. Concatenate markdown results from all pages
    5. Cache result and return
    6. Fallback: return empty string
    """
    if not settings.MISTRAL_API_KEY:
        log.warning("MISTRAL_API_KEY not configured, OCR skipped")
        return ""

    # Check Cache first
    cached_text = await cache_service.get("mistral_ocr", file_url)
    if cached_text:
        log.info("OCR cache hit", url=file_url)
        return cached_text

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
                    full_text = full_text.strip()
                    log.info("OCR extraction successful via Mistral", pages=len(pages), chars=len(full_text))
                    
                    # Cache result for 1 hour (3600 seconds)
                    await cache_service.set("mistral_ocr", file_url, full_text, expire=3600)
                    
                    return full_text
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
