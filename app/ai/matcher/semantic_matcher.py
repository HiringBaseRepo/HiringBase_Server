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
_DEFAULT_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"


@lru_cache(maxsize=1)
def _get_model():
    """Load model satu kali dan cache (singleton)."""
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(_DEFAULT_MODEL)
        log.info("SentenceTransformer model loaded", model=_DEFAULT_MODEL)
        return model
    except ImportError:
        log.warning("sentence-transformers not installed, falling back to exact match only")
        return None
    except Exception as exc:
        log.error("Failed to load SentenceTransformer model", error=str(exc))
        return None


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


def _semantic_match(
    required_skill: str,
    candidate_skills: List[str],
    model,
    threshold: float = SEMANTIC_THRESHOLD,
) -> bool:
    """Cek semantic similarity menggunakan sentence-transformers."""
    if not candidate_skills or model is None:
        return False

    try:
        import numpy as np

        query_emb = model.encode([required_skill], convert_to_tensor=False)
        cand_embs = model.encode(candidate_skills, convert_to_tensor=False)

        # Cosine similarity manual (lebih portable)
        def cosine_sim(a, b):
            a_norm = a / (np.linalg.norm(a) + 1e-9)
            b_norm = b / (np.linalg.norm(b) + 1e-9)
            return float(np.dot(a_norm, b_norm))

        for i, cand_emb in enumerate(cand_embs):
            sim = cosine_sim(query_emb[0], cand_emb)
            if sim >= threshold:
                log.debug(
                    "Semantic skill match",
                    required=required_skill,
                    candidate=candidate_skills[i],
                    similarity=round(sim, 3),
                )
                return True

    except Exception as exc:
        log.warning("Semantic matching error", error=str(exc))

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
    Layer 3: Cosine semantic similarity via sentence-transformers

    Returns:
        match_percentage, matched_skills, missing_skills, confidence_score
    """
    raw_candidate_skills: List[str] = candidate_data.get("skills", [])
    candidate_skills_lower = set(s.lower() for s in raw_candidate_skills)
    candidate_skills_list = [s.lower() for s in raw_candidate_skills]
    synonyms = _synonym_map()
    model = _get_model()

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
    match_methods: Dict[str, str] = {}

    for req_skill in required_skills:
        # Layer 1 & 2: exact + synonym
        if _exact_and_synonym_match(req_skill, candidate_skills_lower, synonyms):
            matched.append(req_skill)
            match_methods[req_skill] = "exact/synonym"
            continue

        # Layer 3: semantic embedding
        if model is not None and candidate_skills_list:
            if _semantic_match(req_skill, candidate_skills_list, model):
                matched.append(f"{req_skill} (semantic)")
                match_methods[req_skill] = "semantic"
                continue

        missing.append(req_skill)

    total = len(required_skills)
    match_pct = (len(matched) / total) * 100.0 if total > 0 else 0.0

    # Confidence lebih tinggi jika model semantic tersedia
    confidence = 0.90 if model is not None else 0.70

    return {
        "match_percentage": round(min(match_pct, 100.0), 2),
        "matched_skills": matched,
        "missing_skills": missing,
        "confidence_score": confidence,
    }
