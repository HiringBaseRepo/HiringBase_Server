"""AI Scoring orchestration engine."""
from typing import Dict, Any, Optional
from app.ai.parser.resume_parser import parse_resume_text
from app.ai.matcher.semantic_matcher import match_candidate_to_job
from app.ai.redflag.detector import detect_red_flags
from app.ai.explanation.generator import generate_explanation
from app.ai.llm.client import generate_llm_explanation


async def score_candidate(
    resume_text: str,
    job_requirements: list,
    job_description: str,
    weights: Dict[str, int],
) -> Dict[str, Any]:
    """Full AI scoring pipeline for a candidate."""
    parsed = parse_resume_text(resume_text)
    match = await match_candidate_to_job(parsed, job_requirements, job_description)

    # Placeholder scores for other dimensions
    exp_score = 70.0
    edu_score = 70.0
    portfolio_score = 60.0
    soft_skill_score = 65.0
    admin_score = 80.0

    final = (
        match["match_percentage"] * weights.get("skill_match", 40) +
        exp_score * weights.get("experience", 20) +
        edu_score * weights.get("education", 10) +
        portfolio_score * weights.get("portfolio", 10) +
        soft_skill_score * weights.get("soft_skill", 10) +
        admin_score * weights.get("administrative", 10)
    ) / 100.0

    red_flags = detect_red_flags(parsed, resume_text)
    explanation = generate_explanation(match, exp_score, edu_score, portfolio_score, soft_skill_score, admin_score, final)

    return {
        "final_score": round(final, 2),
        "skill_match_score": round(match["match_percentage"], 2),
        "experience_score": round(exp_score, 2),
        "education_score": round(edu_score, 2),
        "portfolio_score": round(portfolio_score, 2),
        "soft_skill_score": round(soft_skill_score, 2),
        "administrative_score": round(admin_score, 2),
        "explanation": explanation,
        "red_flags": red_flags,
    }
