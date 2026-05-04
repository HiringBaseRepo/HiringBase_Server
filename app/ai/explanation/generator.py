"""Explainable AI — score reasoning generator."""
from typing import Dict


def generate_explanation(
    match_result: Dict,
    exp_score: float,
    edu_score: float,
    portfolio_score: float,
    soft_skill_score: float,
    admin_score: float,
    final_score: float,
    red_flags: Dict = None,
) -> str:
    """Generate human-readable explanation for candidate score."""
    parts = []
    parts.append(f"Kandidat memenuhi {len(match_result.get('matched_skills', []))} dari {len(match_result.get('matched_skills', [])) + len(match_result.get('missing_skills', []))} kriteria utama.")

    if match_result.get("matched_skills"):
        top_skills = match_result["matched_skills"][:3]
        parts.append(f"Skill utama yang sesuai: {', '.join(top_skills)}.")

    if exp_score >= 80:
        parts.append("Pengalaman kerja memenuhi syarat.")
    elif exp_score >= 50:
        parts.append("Pengalaman kerja cukup relevan.")
    else:
        parts.append("Pengalaman kerja masih perlu dipertimbangkan.")

    if edu_score >= 80:
        parts.append("Pendidikan relevan.")

    if portfolio_score >= 60:
        parts.append("Portfolio tersedia.")

    if final_score >= 75:
        parts.append("Direkomendasikan lanjut interview.")
    elif final_score >= 60:
        parts.append("Cukup menarik untuk ditinjau lebih lanjut.")
    else:
        parts.append("Perlu pertimbangan HR sebelum lanjut.")

    if red_flags and red_flags.get("red_flags"):
        doc_warns = [f for f in red_flags["red_flags"] if "Peringatan" in f]
        if doc_warns:
            parts.append("Perhatian: Terdapat anomali pada verifikasi dokumen administrasi.")

    return " ".join(parts)
