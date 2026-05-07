"""Red flag detection engine."""
from typing import Dict, List, Any
import re
import json
import structlog
from app.ai.llm.client import call_llm

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
            flags.append("Terdeteksi celah karir (employment gap) yang signifikan")

    # Job hopping
    if len(experiences) >= 4:
        total_years = sum(e.get("years", 0) for e in experiences)
        avg_years = total_years / len(experiences) if len(experiences) > 0 else 0
        if avg_years < 1:
            flags.append("Potensi pola berpindah-pindah kerja (job hopping)")

    # Too many typos
    words = raw_text.split()
    if len(words) > 20:
        typo_patterns = re.findall(
            r"\b(teh|adn|hte|recieve|seperate)\b", raw_text.lower()
        )
        if len(typo_patterns) > 3:
            flags.append("Tingkat kesalahan pengetikan (typo) tinggi pada dokumen")

    # Salary unrealistic placeholder check
    salary_matches = re.findall(r"\b(100\s*juta|1\s*miliar)\b", raw_text.lower())
    if salary_matches:
        flags.append("Ekspektasi gaji tidak realistis (nilai placeholder)")

    return flags


async def detect_red_flags(parsed_data: Dict, raw_text: str, force_fallback: bool = False) -> Dict[str, Any]:
    """Detect risk indicators in candidate profile using semantic LLM analysis with regex fallback."""
    flags = []
    risk_level = "low"

    # LLM Prompt for Red Flag Analysis in Indonesian
    prompt = f"""Identifikasi potensi red flag atau risiko profesional untuk kandidat ini dalam Bahasa Indonesia.
Data Kandidat: {json.dumps(parsed_data, default=str)}
Potongan teks dokumen: {raw_text[:1000]}

Fokus pada:
1. Celah karir (employment gaps) atau inkonsistensi yang signifikan.
2. Pola kutu loncat (job hopping).
3. Inkonsistensi logis antar peran/pengalaman.
4. Masalah profesionalisme.

Kembalikan HANYA daftar poin (bullet-point) red flag yang terdeteksi. Jika tidak ada, kembalikan 'Tidak ada'.
"""
    try:
        llm_response = await call_llm(prompt, max_tokens=256)
        if llm_response and "None" not in llm_response:
            # Simple bullet point parsing
            llm_flags = [
                line.strip("- ").strip()
                for line in llm_response.split("\n")
                if line.strip() and (line.startswith("-") or line.strip()[0].isdigit())
            ]
            flags.extend(llm_flags)
    except Exception as exc:
        log.warning("LLM red flag detection failed", error=str(exc))
        if not force_fallback:
            # Raise exception to trigger Taskiq retry if not on last attempt
            raise AIAPIException(f"LLM red flag detection failed: {str(exc)}")

    # Always include regex flags as baseline or fallback
    regex_flags = _detect_red_flags_regex(parsed_data, raw_text)
    for rf in regex_flags:
        if rf not in flags:
            flags.append(rf)

    # Determine risk
    if len(flags) >= 3:
        risk_level = "high"
    elif len(flags) >= 1:
        risk_level = "medium"

    return {
        "red_flags": flags,
        "risk_level": risk_level,
    }
