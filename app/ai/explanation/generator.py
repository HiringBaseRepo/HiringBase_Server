from typing import Dict, Any, Optional
import structlog
from app.ai.llm.client import call_llm

log = structlog.get_logger(__name__)

async def generate_explanation(
    match_result: Dict[str, Any],
    exp_score: float,
    edu_score: float,
    portfolio_score: float,
    soft_skill_score: float,
    admin_score: float,
    final_score: float,
    red_flags: Dict[str, Any] = None,
    scoring_breakdown: Dict[str, Any] | None = None,
) -> str:
    """Generate human-readable explanation for candidate score using LLM with Template Fallback."""
    
    # Try LLM first
    llm_explanation = await _generate_llm_explanation(
        match_result, exp_score, edu_score, portfolio_score, 
        soft_skill_score, admin_score, final_score, red_flags, scoring_breakdown
    )
    if llm_explanation:
        return llm_explanation

    # Fallback to Template
    return _generate_template_explanation(
        match_result, exp_score, edu_score, portfolio_score, 
        soft_skill_score, admin_score, final_score, red_flags, scoring_breakdown
    )


async def _generate_llm_explanation(
    match_result: Dict,
    exp_score: float,
    edu_score: float,
    portfolio_score: float,
    soft_skill_score: float,
    admin_score: float,
    final_score: float,
    red_flags: Dict = None,
    scoring_breakdown: Dict | None = None,
) -> Optional[str]:
    """Generate natural language explanation using LLM (Groq) in Indonesian."""
    confidence_note = ""
    gate_reasons = []
    if scoring_breakdown:
        gate_reasons = scoring_breakdown.get("gates", {}).get("reasons", [])
        components = scoring_breakdown.get("components", {})
        skill_component = components.get("skill_match", {})
        confidence_note = (
            f"- Confidence Skill Match: {skill_component.get('confidence', 0)}\n"
            f"- Gate Review: {', '.join(gate_reasons) if gate_reasons else 'tidak ada'}\n"
        )

    prompt = f"""
    Task: Berikan ringkasan evaluasi kandidat untuk HR dalam 2-3 kalimat (Bahasa Indonesia).
    
    Data Skor (0-100):
    - Skill Match: {match_result.get('match_percentage', 0)}% (Cocok: {', '.join(match_result.get('matched_skills', []))})
    - Pengalaman: {exp_score}
    - Edukasi: {edu_score}
    - Portofolio: {portfolio_score}
    - Soft Skill: {soft_skill_score}
    - Administrasi: {admin_score}
    - SKOR AKHIR TOTAL: {final_score}
    {confidence_note}
    
    Anomali/Red Flags: {red_flags.get('red_flags', []) if red_flags else 'Tidak ada'}
    
    Instruksi:
    - Fokus pada kekuatan utama dan alasan pemberian skor akhir.
    - Sebutkan jika ada red flag (risiko) yang serius.
    - Jika confidence skill rendah atau requirement skill tidak terstruktur, sebutkan perlunya review manual.
    - Gunakan nada profesional, lugas, dan ringkas.
    - Output HANYA teks ringkasan summary.
    """
    try:
        return await call_llm(prompt, max_tokens=1024)
    except Exception as exc:
        log.error("LLM explanation failed, falling back to template", error=str(exc))
        return None


def _generate_template_explanation(
    match_result: Dict,
    exp_score: float,
    edu_score: float,
    portfolio_score: float,
    soft_skill_score: float,
    admin_score: float,
    final_score: float,
    red_flags: Dict = None,
    scoring_breakdown: Dict | None = None,
) -> str:
    """Generate human-readable explanation using rule-based template in Indonesian."""
    parts = []
    total_matched = len(match_result.get('matched_skills', []))
    total_req = total_matched + len(match_result.get('missing_skills', []))
    parts.append(f"Kandidat memenuhi {total_matched} dari {total_req} kriteria utama.")

    if match_result.get("matched_skills"):
        top_skills = match_result["matched_skills"][:3]
        parts.append(f"Skill utama yang cocok: {', '.join(top_skills)}.")

    if exp_score >= 80:
        parts.append("Pengalaman kerja sangat sesuai dengan kebutuhan.")
    elif exp_score >= 50:
        parts.append("Pengalaman kerja cukup relevan.")
    else:
        parts.append("Pengalaman kerja memerlukan pertimbangan lebih lanjut.")

    if edu_score >= 80:
        parts.append("Latar belakang pendidikan relevan.")

    if portfolio_score >= 60:
        parts.append("Portofolio tersedia dan mendukung.")

    if final_score >= 75:
        parts.append("Direkomendasikan untuk tahap wawancara.")
    elif final_score >= 60:
        parts.append("Dapat dipertimbangkan untuk review lebih lanjut.")
    else:
        parts.append("Memerlukan tinjauan manual HR sebelum diputuskan.")

    gate_reasons = []
    if scoring_breakdown:
        gate_reasons = scoring_breakdown.get("gates", {}).get("reasons", [])
    if "low_skill_match_confidence" in gate_reasons:
        parts.append("Confidence skill match rendah sehingga kandidat perlu review manual HR.")
    if "insufficient_structured_skill_requirements" in gate_reasons:
        parts.append("Requirement skill terstruktur pada lowongan belum cukup kuat sehingga hasil scoring perlu ditinjau manual.")

    if red_flags and red_flags.get("red_flags"):
        # Handle both dict and legacy string flags
        flags_text = []
        for f in red_flags["red_flags"]:
            if isinstance(f, dict):
                flags_text.append(f.get("message", "").lower())
            else:
                flags_text.append(str(f).lower())
                
        has_anomalies = any(
            "anomaly" in txt or "warning" in txt or "anomali" in txt or "inkonsistensi" in txt 
            for txt in flags_text
        )
        if has_anomalies:
            parts.append("Perhatian: Ditemukan anomali atau inkonsistensi data pada verifikasi dokumen.")

    return " ".join(parts)
