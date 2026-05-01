"""OCR engine for extracting text from documents."""
from typing import Optional
import httpx


def _is_image_url(url: str) -> bool:
    return any(url.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png"])


async def extract_text_from_document(file_url: str) -> str:
    """Extract text from a document URL using OCR or direct text extraction."""
    # For MVP: try to download and use easyocr / pdfplumber approach
    # Stub: if URL is accessible text/PDF, return placeholder or fetch text
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(file_url)
            if resp.status_code == 200:
                # In production: use pdfplumber for PDF, easyocr for images
                # MVP fallback: return empty string to allow manual processing
                content_type = resp.headers.get("content-type", "")
                if "pdf" in content_type:
                    return "[PDF_TEXT_PLACEHOLDER]"
                if "image" in content_type or _is_image_url(file_url):
                    return "[IMAGE_OCR_PLACEHOLDER]"
                return resp.text[:5000]
        except Exception:
            pass
    return ""
