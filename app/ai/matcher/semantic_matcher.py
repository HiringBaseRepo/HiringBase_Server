"""Semantic skill matching engine menggunakan sentence-transformers.

Layer 2 — NLP / Embedding Engine:
- Exact match (cepat, priority 1)
- Synonym map (curated, priority 2)
- Semantic embedding cosine similarity via sentence-transformers (priority 3)

Model default: paraphrase-multilingual-MiniLM-L12-v2
- Support Bahasa Indonesia + Inggris
- Ringan (~100MB) dan bisa jalan di CPU
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, List, Optional

import structlog

log = structlog.get_logger(__name__)

# Threshold cosine similarity untuk dianggap "match"
SEMANTIC_THRESHOLD = 0.65

# Model multilingual agar support kalimat BahasaIndonesia/Inggris
_DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
_HF_API_URL = f"https://api-inference.huggingface.co/models/{_DEFAULT_MODEL}"



def _synonym_map() -> Dict[str, List[str]]:
    """Curated synonym map untuk skill umum di Indonesia."""
    return {
        "customer service": ["client handling", "customer support", "helpdesk", "layanan pelanggan"],
        "node.js": ["backend javascript", "express", "nestjs", "express.js"],
        "react": ["frontend react ecosystem", "next.js", "reactjs", "react.js"],
        "python": ["django", "flask", "fastapi"],
        "project management": ["pm", "scrum master", "agile lead", "manajemen proyek"],
        "microsoft office": ["ms office", "excel", "word", "powerpoint", "office suite"],
        "sql": ["database", "rdbms", "postgresql", "mysql", "mariadb"],
        "machine learning": ["ml", "deep learning", "artificial intelligence", "ai", "data science"],
        "komunikasi": ["communication", "presentasi", "presentation"],
        "kepemimpinan": ["leadership", "team lead", "pemimpin"],
        "teamwork": ["kerjasama tim", "kolaborasi", "collaboration"],
        "akuntansi": ["accounting", "pajak", "tax", "finance", "keuangan"],
        "desain grafis": ["graphic design", "adobe photoshop", "illustrator", "canva", "desain"],
        "content creator": ["copywriting", "video editing", "konten kreator", "social media manager"],
        "pemasaran": ["marketing", "digital marketing", "seo", "sem", "ads", "iklan"],
    }


def _exact_and_synonym_match(
    skill: str,
    candidate_skills: set[str],
    synonyms: Dict[str, List[str]],
) -> bool:
    """Cek exact match + synonym match."""
    if skill in candidate_skills:
        return True

    # Cek apakah skill ada di synonym groups
    for key, syns in synonyms.items():
        group = {key} | set(syns)
        if skill in group:
            # Cek apakah kandidat punya salah satu dari group
            if candidate_skills & group:
                return True

    return False


from app.core.cache.service import cache_service

async def _semantic_match(
    required_skill: str,
    candidate_skills: List[str],
    hf_token: Optional[str],
    threshold: float = SEMANTIC_THRESHOLD,
) -> bool:
    """Cek semantic similarity menggunakan Hugging Face Inference API dengan Redis caching."""
    if not candidate_skills or not hf_token:
        log.warning("Semantic matching skipped: no candidate skills or HF_TOKEN missing")
        return False

    # Cache key based on input pair
    # Sort candidate skills to ensure deterministic key
    cache_id = f"{required_skill}:{','.join(sorted(candidate_skills))}"
    
    cached_result = await cache_service.get("hf_match", cache_id)
    if cached_result is not None:
        log.debug("Semantic match cache hit", required=required_skill)
        return cached_result

    try:
        import httpx

        headers = {"Authorization": f"Bearer {hf_token}"}
        payload = {
            "inputs": {
                "source_sentence": required_skill,
                "sentences": candidate_skills,
            }
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(_HF_API_URL, headers=headers, json=payload)
            
            if response.status_code == 200:
                scores = response.json()
                is_match = False
                # scores adalah list of floats yang merepresentasikan similarity
                for i, score in enumerate(scores):
                    if score >= threshold:
                        log.debug(
                            "Semantic skill match (HF API)",
                            required=required_skill,
                            candidate=candidate_skills[i],
                            similarity=round(score, 3),
                        )
                        is_match = True
                        break
                
                # Cache the boolean result for 1 day (86400 seconds)
                await cache_service.set("hf_match", cache_id, is_match, expire=86400)
                return is_match
            else:
                log.warning(
                    "HF Inference API error",
                    status_code=response.status_code,
                    response=response.text,
                )

    except Exception as exc:
        log.warning("Semantic matching API error", error=str(exc))

    return False



async def match_candidate_to_job(
    candidate_data: Dict[str, Any],
    job_requirements: List[Any],
    job_description: str,
    force_fallback: bool = False,
) -> Dict[str, Any]:
    """Match skill kandidat ke requirement lowongan dengan 3-layer matching.

    Layer 1: Exact string match
    Layer 2: Curated synonym match
    Layer 3: Cosine semantic similarity via Hugging Face Inference API

    Returns:
        match_percentage, matched_skills, missing_skills, confidence_score
    """
    from app.core.config import settings

    raw_candidate_skills: List[str] = candidate_data.get("skills", [])
    candidate_skills_lower = set(s.lower() for s in raw_candidate_skills)
    candidate_skills_list = [s.lower() for s in raw_candidate_skills]
    synonyms = _synonym_map()
    hf_token = settings.HF_TOKEN

    # Kumpulkan required skills dari job_requirements
    required_skills: List[str] = []
    for req in job_requirements:
        if hasattr(req, "category"):
            # SQLAlchemy model
            if req.category == "skill":
                required_skills.append(req.name.lower())
        elif isinstance(req, dict) and req.get("category") == "skill":
            required_skills.append(req.get("name", "").lower())

    # Fallback: ambil kata signifikan dari job description
    if not required_skills and job_description:
        words = [w.lower() for w in job_description.split() if len(w) > 4]
        # Deduplicate + limit
        seen: set[str] = set()
        for w in words:
            if w not in seen:
                required_skills.append(w)
                seen.add(w)
            if len(required_skills) >= 20:
                break

    if not required_skills:
        return {
            "match_percentage": 0.0,
            "matched_skills": [],
            "missing_skills": [],
            "confidence_score": 0.0,
        }

    matched: List[str] = []
    missing: List[str] = []

    for req_skill in required_skills:
        # Layer 1 & 2: exact + synonym
        if _exact_and_synonym_match(req_skill, candidate_skills_lower, synonyms):
            matched.append(req_skill)
            continue

        # Layer 3: semantic embedding via HF API
        if hf_token and candidate_skills_list:
            if await _semantic_match(req_skill, candidate_skills_list, hf_token):
                matched.append(f"{req_skill} (semantic)")
                continue

        missing.append(req_skill)

    total = len(required_skills)
    match_pct = (len(matched) / total) * 100.0 if total > 0 else 0.0

    # Confidence lebih tinggi jika HF API tersedia
    confidence = 0.90 if hf_token else 0.70

    return {
        "match_percentage": round(min(match_pct, 100.0), 2),
        "matched_skills": matched,
        "missing_skills": missing,
        "confidence_score": confidence,
    }
