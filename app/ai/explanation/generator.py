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
) -> str:
    """Generate human-readable explanation for candidate score using LLM with Template Fallback."""
    
    # Try LLM first
    llm_explanation = await _generate_llm_explanation(
        match_result, exp_score, edu_score, portfolio_score, 
        soft_skill_score, admin_score, final_score, red_flags
    )
    if llm_explanation:
        return llm_explanation

    # Fallback to Template
    return _generate_template_explanation(
        match_result, exp_score, edu_score, portfolio_score, 
        soft_skill_score, admin_score, final_score, red_flags
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
) -> Optional[str]:
    """Generate natural language explanation using LLM (Groq) in Indonesian."""
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
    
    Anomali/Red Flags: {red_flags.get('red_flags', []) if red_flags else 'Tidak ada'}
    
    Instruksi:
    - Fokus pada kekuatan utama dan alasan pemberian skor akhir.
    - Sebutkan jika ada red flag (risiko) yang serius.
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
