"""Semantic skill matching engine."""
from typing import List, Dict, Any


def _synonym_map():
    return {
        "customer service": ["client handling", "customer support", "helpdesk"],
        "node.js": ["backend javascript", "express", "nestjs"],
        "react": ["frontend react ecosystem", "next.js", "reactjs"],
        "python": ["django", "flask", "fastapi"],
        "project management": ["pm", "scrum master", "agile lead"],
    }


async def match_candidate_to_job(candidate_data: Dict[str, Any], job_requirements: List[Any], job_description: str) -> Dict[str, Any]:
    """Match candidate skills to job requirements."""
    candidate_skills = set(s.lower() for s in candidate_data.get("skills", []))
    synonyms = _synonym_map()

    required_skills = []
    for req in job_requirements:
        if req.category == "skill":
            required_skills.append(req.name.lower())

    if not required_skills:
        required_skills = [w.lower() for w in job_description.split() if len(w) > 3]

    matched = []
    missing = []

    for req in required_skills:
        if req in candidate_skills:
            matched.append(req)
            continue
        # Check synonyms
        found = False
        for key, syns in synonyms.items():
            if req == key or req in syns:
                if any(s in candidate_skills for s in [key] + syns):
                    matched.append(f"{req} (via synonym)")
                    found = True
                    break
        if not found:
            missing.append(req)

    total = len(required_skills) if required_skills else 1
    match_pct = (len(matched) / total) * 100.0

    return {
        "match_percentage": round(min(match_pct, 100.0), 2),
        "matched_skills": matched,
        "missing_skills": missing,
        "confidence_score": 0.85,
    }
