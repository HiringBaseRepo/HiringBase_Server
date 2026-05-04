"""Semantic Document Validator using LLM (Groq)."""
import json
import httpx
import structlog
from typing import Dict, Any, Optional
from app.core.config import settings

log = structlog.get_logger(__name__)

async def validate_document_content(
    doc_type: str,
    ocr_text: str,
    applicant_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Validasi konten dokumen (KTP, Ijazah) menggunakan LLM Groq.
    Membandingkan teks hasil OCR dengan data pendaftar.
    
    Returns:
        Dict: { "valid": bool, "reason": str, "confidence": float }
    """
    if not settings.GROQ_API_KEY:
        log.warning("GROQ_API_KEY not configured, skipping semantic document validation")
        return {"valid": True, "reason": "Validator skipped (no API key)", "confidence": 1.0}
    
    if not ocr_text or len(ocr_text.strip()) < 10:
        return {
            "valid": False, 
            "reason": f"Teks hasil OCR {doc_type} terlalu pendek atau tidak terbaca", 
            "confidence": 0.0
        }

    # Prompt Engineering
    prompt = f"""
    Tugas: Validasi dokumen HR (Hiring Assistant).
    Bandingkan teks hasil OCR dari dokumen {doc_type} dengan data profil pelamar.
    
    Data Pelamar:
    - Nama Lengkap: {applicant_data.get('name')}
    - Email: {applicant_data.get('email')}
    
    Teks Hasil OCR dari {doc_type}:
    ---
    {ocr_text[:4000]}
    ---
    
    Instruksi:
    1. Periksa apakah Nama di dalam dokumen cocok dengan Nama Pelamar (toleransi perbedaan ejaan kecil).
    2. Periksa apakah tipe dokumen yang dibaca benar-benar merupakan {doc_type}.
    3. Periksa masa berlaku dokumen (jika ada). Pastikan tanggal berlaku masih aktif atau seumur hidup.
    4. Periksa apakah terdapat format nomor dokumen yang valid (misal: NIK untuk KTP, Nomor Ijazah untuk Ijazah).
    5. Identifikasi jika ada indikasi dokumen milik orang lain, hasil rekayasa teks, atau tidak wajar.
    
    Respon WAJIB dalam format JSON saja:
    {{
        "valid": boolean,
        "reason": "penjelasan singkat dalam Bahasa Indonesia",
        "confidence": float (0.0 sampai 1.0)
    }}
    """

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.GROQ_MODEL,
                    "messages": [
                        {"role": "system", "content": "You are a professional HR document verifier. Output JSON only."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"}
                },
            )
            
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                result = json.loads(content)
                log.info("Document validation result", doc_type=doc_type, valid=result.get("valid"))
                return result
            else:
                log.error("Groq API error", status_code=resp.status_code, body=resp.text)
                return {"valid": True, "reason": "Kesalahan API (Fallback ke Pass)", "confidence": 0.5}
                
    except Exception as exc:
        log.error("Document validation exception", error=str(exc))
        return {"valid": True, "reason": "Kesalahan internal validator", "confidence": 0.5}
