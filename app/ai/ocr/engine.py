"""OCR engine untuk ekstraksi teks dari dokumen CV dan lampiran.

Strategy:
- PDF: gunakan pdfplumber (text-based PDF) → fallback PyMuPDF-raw
- Image (JPG/PNG): gunakan EasyOCR
- Download file via httpx dari Cloudflare R2 ke BytesIO sebelum proses
- Semua error di-log dan tidak memblokir pipeline
"""
from __future__ import annotations

import io
import logging
from typing import Optional

import httpx
import structlog

log = structlog.get_logger(__name__)

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}


def _is_image(url: str, content_type: str) -> bool:
    url_lower = url.lower().split("?")[0]  # strip query params
    ext_match = any(url_lower.endswith(ext) for ext in _IMAGE_EXTS)
    ct_match = "image" in content_type
    return ext_match or ct_match


def _extract_text_pdf(content: bytes) -> str:
    """Ekstrak teks dari konten PDF menggunakan pdfplumber."""
    try:
        import pdfplumber

        all_text: list[str] = []
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text(x_tolerance=3, y_tolerance=3)
                if page_text:
                    all_text.append(page_text.strip())

        result = "\n".join(all_text).strip()
        if result:
            return result
    except ImportError:
        log.warning("pdfplumber not installed, PDF extraction skipped")
    except Exception as exc:
        log.warning("pdfplumber extraction failed", error=str(exc))

    return ""


def _extract_text_image(content: bytes) -> str:
    """Ekstrak teks dari image menggunakan EasyOCR."""
    try:
        import easyocr
        import numpy as np
        from PIL import Image

        image = Image.open(io.BytesIO(content)).convert("RGB")
        img_array = np.array(image)

        # Inisialisasi reader (GPU=False untuk portabilitas)
        reader = easyocr.Reader(["id", "en"], gpu=False, verbose=False)
        results = reader.readtext(img_array, detail=0, paragraph=True)
        return "\n".join(results).strip()

    except ImportError:
        log.warning("easyocr or PIL not installed, image OCR skipped")
    except Exception as exc:
        log.warning("EasyOCR extraction failed", error=str(exc))

    return ""


async def _download_file(file_url: str) -> tuple[bytes, str]:
    """Download file dari URL, kembalikan (content, content_type)."""
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        resp = await client.get(file_url)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        return resp.content, content_type


async def extract_text_from_document(file_url: str) -> str:
    """Ekstrak teks dari URL dokumen (PDF atau image).

    Flow:
    1. Download file dari URL
    2. Deteksi tipe (PDF/image)
    3. Proses dengan engine yang sesuai
    4. Fallback: kembalikan string kosong (tidak memblokir pipeline)

    Args:
        file_url: URL publik file di Cloudflare R2

    Returns:
        Teks hasil ekstraksi, atau string kosong jika gagal
    """
    try:
        content, content_type = await _download_file(file_url)
    except Exception as exc:
        log.error("Failed to download document for OCR", url=file_url, error=str(exc))
        return ""

    if not content:
        return ""

    url_lower = file_url.lower().split("?")[0]

    # PDF: coba pdfplumber
    if "pdf" in content_type or url_lower.endswith(".pdf"):
        text = _extract_text_pdf(content)
        if text:
            log.info("PDF text extracted via pdfplumber", chars=len(text))
            return text
        log.warning("pdfplumber returned empty text, document may be image-based PDF", url=file_url)
        # Image-based PDF: coba OCR pada byte raw sebagai fallback
        # (tidak convert ke image di MVP — tandai untuk manual review)
        return ""

    # Image: gunakan EasyOCR
    if _is_image(file_url, content_type):
        text = _extract_text_image(content)
        if text:
            log.info("Image text extracted via EasyOCR", chars=len(text))
            return text
        log.warning("EasyOCR returned empty text", url=file_url)
        return ""

    # Fallback: coba baca sebagai plain text
    try:
        return content.decode("utf-8", errors="ignore")[:8000]
    except Exception:
        return ""
