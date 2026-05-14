import json
import re
from typing import Any, Dict, List
import structlog
from app.ai.llm.client import call_llm
from app.shared.enums.risk_level import RiskLevel

log = structlog.get_logger(__name__)


def _detect_red_flags_regex(parsed_data: Dict, raw_text: str) -> List[str]:
    """Deterministic regex-based fallback for red flag detection in Indonesian."""
    flags = []

    # Employment gap
    experiences = parsed_data.get("experiences", [])
    if len(experiences) > 1:
        gaps = []
        for i in range(1, len(experiences)):
            prev_end = experiences[i - 1].get("end", 0)
            curr_start = experiences[i].get("start", 0)
            if curr_start - prev_end > 1:
                gaps.append(curr_start - prev_end)
        if any(g > 2 for g in gaps):
            flags.append({
                "message": "Terdeteksi celah karir (employment gap) yang signifikan",
                "risk_level": RiskLevel.MEDIUM.value,
                "type": "professional"
            })

    # Job hopping
    if len(experiences) >= 4:
        total_years = sum(e.get("years", 0) for e in experiences)
        avg_years = total_years / len(experiences) if len(experiences) > 0 else 0
        if avg_years < 1:
            flags.append({
                "message": "Potensi pola berpindah-pindah kerja (job hopping)",
                "risk_level": RiskLevel.MEDIUM.value,
                "type": "professional"
            })

    # Content integrity
    if any(k in raw_text.lower() for k in ["fake", "modified", "edit"]):
        flags.append({
            "message": "Potensi manipulasi dokumen terdeteksi (kata kunci mencurigakan).",
            "risk_level": RiskLevel.HIGH.value,
            "type": "content"
        })
    
    # Check for empty text
    if not raw_text.strip() and not parsed_data:
        flags.append({
            "message": "Data pendaftaran sangat minim atau kosong.",
            "risk_level": RiskLevel.MEDIUM.value,
            "type": "system"
        })

    # Too many typos
    words = raw_text.split()
    if len(words) > 20:
        typo_patterns = re.findall(
            r"\b(teh|adn|hte|recieve|seperate)\b", raw_text.lower()
        )
        if len(typo_patterns) > 3:
            flags.append({
                "message": "Tingkat kesalahan pengetikan (typo) tinggi pada dokumen",
                "risk_level": RiskLevel.LOW.value,
                "type": "quality"
            })

    # Salary unrealistic placeholder check
    salary_matches = re.findall(r"\b(100\s*juta|1\s*miliar)\b", raw_text.lower())
    if salary_matches:
        flags.append(
            {
                "message": "Ekspektasi gaji tidak realistis (nilai placeholder)",
                "risk_level": RiskLevel.MEDIUM.value,
                "type": "professional",
            }
        )

    return flags


async def detect_red_flags(
    parsed_data: Dict, 
    raw_text: str, 
    doc_ocr_results: Dict[str, str] = None,
    force_fallback: bool = False
) -> Dict[str, Any]:
    """Detect risk indicators in candidate profile using semantic LLM analysis with regex fallback."""
    flags = []
    risk_level = RiskLevel.LOW.value

    # 1. Check for data inconsistencies if OCR results are provided
    if doc_ocr_results:
        inconsistency_flags = await _detect_data_inconsistencies(parsed_data, doc_ocr_results, force_fallback)
        flags.extend(inconsistency_flags)

    # LLM Prompt for Red Flag Analysis in Indonesian
    prompt = f"""Identifikasi potensi red flag atau risiko profesional untuk kandidat ini dalam Bahasa Indonesia.
Data Kandidat: {json.dumps(parsed_data, default=str)}
Potongan teks dokumen: {raw_text[:1000]}
{"OCR Dokumen: " + json.dumps({k: v[:500] for k, v in doc_ocr_results.items()}) if doc_ocr_results else ""}

Fokus pada:
1. Celah karir (employment gaps) atau inkonsistensi yang signifikan.
2. Pola kutu loncat (job hopping).
3. Inkonsistensi logis antar peran/pengalaman.
4. Masalah profesionalisme.

Kembalikan HANYA daftar poin (bullet-point) red flag yang terdeteksi. Jika tidak ada, kembalikan 'Tidak ada'.
"""
    try:
        llm_response = await call_llm(prompt, max_tokens=256)
        if llm_response and "None" not in llm_response and "Tidak ada" not in llm_response:
            # Simple bullet point parsing
            llm_flags = [
                line.strip("- ").strip()
                for line in llm_response.split("\n")
                if line.strip() and (line.startswith("-") or line.strip()[0].isdigit())
            ]
            for f in llm_flags:
                if f not in flags:
                    flags.append(
                        {
                            "message": f,
                            "risk_level": RiskLevel.MEDIUM.value,
                            "type": "ai_analysis",
                        }
                    )
    except Exception as exc:
        log.warning("LLM red flag detection failed", error=str(exc))
        if not force_fallback:
            from app.core.exceptions.custom_exceptions import AIAPIException
            raise AIAPIException(f"LLM red flag detection failed: {str(exc)}")

    # Always include regex flags as baseline or fallback
    regex_flags = _detect_red_flags_regex(parsed_data, raw_text)
    for rf in regex_flags:
        if rf not in flags:
            flags.append(rf)

    # Determine risk
    risk_level = RiskLevel.LOW.value
    if any(
        "inkonsistensi" in f.get("message", "").lower()
        or "palsu" in f.get("message", "").lower()
        for f in flags
        if isinstance(f, dict)
    ):
        risk_level = RiskLevel.HIGH.value
    elif any(
        f.get("risk_level") == RiskLevel.HIGH.value
        for f in flags
        if isinstance(f, dict)
    ):
        risk_level = RiskLevel.HIGH.value
    elif len(flags) >= 3:
        risk_level = RiskLevel.HIGH.value
    elif len(flags) >= 1:
        risk_level = RiskLevel.MEDIUM.value

    return {
        "red_flags": flags,
        "risk_level": risk_level,
    }


async def _detect_data_inconsistencies(parsed_data: Dict, doc_ocr_results: Dict[str, str], force_fallback: bool = False) -> List[Dict]:
    """Detect inconsistencies between form data and OCR results using LLM."""
    inconsistencies = []
    
    # Identity Check (Name Mismatch) is now handled in validator_step.py
    prompt = f"""Analisis inkonsistensi data antara data profil dan hasil OCR dokumen.
    Data: {json.dumps(parsed_data)}
    OCR: {json.dumps(doc_ocr_results)}
    
    Misal: Jika lulus 2024 tapi klaim pengalaman 5 tahun, itu inkonsisten.
    
    Kembalikan daftar inkonsistensi dalam Bahasa Indonesia poin demi poin. Jika konsisten, kembalikan 'KONSISTEN'.
    """
    try:
        res = await call_llm(prompt, max_tokens=150)
        if res and "KONSISTEN" not in res.upper():
            lines = [line.strip("- ").strip() for line in res.split("\n") if line.strip() and (line.startswith("-") or line.strip()[0].isdigit())]
            for line in lines:
                inconsistencies.append({
                    "message": line,
                    "risk_level": RiskLevel.MEDIUM.value,
                    "type": "ai_analysis"
                })
    except Exception:
        pass
        
    return inconsistencies
