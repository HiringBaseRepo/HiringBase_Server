"""AI Scoring orchestration engine — standalone (non-pipeline).

Digunakan untuk scoring individual atau re-scoring.
Pipeline scoring (dengan DB) ada di screening/router.py.
"""
from typing import Dict, Any, Optional
from app.ai.parser.resume_parser import parse_resume_text
from app.ai.matcher.semantic_matcher import match_candidate_to_job
from app.ai.redflag.detector import detect_red_flags
from app.ai.explanation.generator import generate_explanation
from app.ai.llm.client import generate_llm_explanation


def _score_experience_standalone(years: int, required_str: str) -> float:
    """Hitung experience score dari tahun pengalaman vs requirement."""
    try:
        req = int(required_str)
    except (ValueError, TypeError):
        req = 0
    if req <= 0:
        return 100.0
    if years >= req:
        return 100.0
    return round((years / req) * 100.0, 2)


def _score_education_standalone(education: list, required: str) -> float:
    """Hitung education score berdasarkan ranking level pendidikan."""
    from app.shared.constants.scoring import EDUCATION_RANK
    if not required:
        return 100.0
    if not education:
        return 0.0
    req_rank = EDUCATION_RANK.get(required.lower().replace(".", "").replace(" ", ""), 1)
    cand_rank = 1
    for e in education:
        level = str(e.get("level", "")).lower().replace(".", "").replace(" ", "")
        cand_rank = max(cand_rank, EDUCATION_RANK.get(level, 1))
    if cand_rank >= req_rank:
        return 100.0
    return round((cand_rank / req_rank) * 100.0, 2)


def _score_portfolio_standalone(parsed: dict) -> float:
    """Hitung portfolio score dari URL yang ditemukan di CV."""
    has_github = bool(parsed.get("github_url"))
    has_portfolio = bool(parsed.get("portfolio_url"))
    has_live = bool(parsed.get("live_project_url"))
    if has_github and has_live:
        return 100.0
    if has_github:
        return 75.0
    if has_portfolio:
        return 60.0
    return 0.0


async def score_candidate(
    resume_text: str,
    job_requirements: list,
    job_description: str,
    weights: Dict[str, int],
    required_experience: str = "0",
    required_education: str = "",
) -> Dict[str, Any]:
    """Full AI scoring pipeline standalone untuk satu kandidat.

    Args:
        resume_text: Teks hasil OCR/parsing CV
        job_requirements: List JobRequirement objects atau dicts
        job_description: Deskripsi pekerjaan
        weights: Dict bobot per dimensi (dari JobScoringTemplate)
        required_experience: String angka tahun pengalaman minimum
        required_education: Level pendidikan minimum (s1, d3, dll)

    Returns:
        Dict lengkap dengan semua score dan explanation
    """
    # Parse CV
    parsed = parse_resume_text(resume_text)

    # Layer 2: Semantic matching
    match = await match_candidate_to_job(parsed, job_requirements, job_description)

    # Experience score (dari data CV yang di-parse)
    exp_years = parsed.get("total_years_experience", 0)
    exp_score = _score_experience_standalone(exp_years, required_experience)

    # Education score
    education = parsed.get("education", [])
    edu_score = _score_education_standalone(education, required_education)

    # Portfolio score
    portfolio_score = _score_portfolio_standalone(parsed)

    # Soft skill: MVP default (akan diupdate via NLP engine)
    soft_skill_score = 60.0

    # Admin score: default asumsi lolos jika dipanggil standalone
    admin_score = 100.0

    # Final weighted score
    final = (
        match["match_percentage"] * weights.get("skill_match", 40) +
        exp_score * weights.get("experience", 20) +
        edu_score * weights.get("education", 10) +
        portfolio_score * weights.get("portfolio", 10) +
        soft_skill_score * weights.get("soft_skill", 10) +
        admin_score * weights.get("administrative", 10)
    ) / 100.0

    # Red flag detection
    red_flags = detect_red_flags(parsed, resume_text)

    # Explanation (template-based, LLM optional)
    explanation = generate_explanation(
        match, exp_score, edu_score, portfolio_score, soft_skill_score, admin_score, final
    )

    return {
        "final_score": round(final, 2),
        "skill_match_score": round(match["match_percentage"], 2),
        "experience_score": round(exp_score, 2),
        "education_score": round(edu_score, 2),
        "portfolio_score": round(portfolio_score, 2),
        "soft_skill_score": round(soft_skill_score, 2),
        "administrative_score": round(admin_score, 2),
        "matched_skills": match.get("matched_skills", []),
        "missing_skills": match.get("missing_skills", []),
        "explanation": explanation,
        "red_flags": red_flags,
        "parsed_data": {
            "name": parsed.get("name"),
            "skills": parsed.get("skills", []),
            "total_years_experience": parsed.get("total_years_experience", 0),
            "education": parsed.get("education", []),
        },
    }
