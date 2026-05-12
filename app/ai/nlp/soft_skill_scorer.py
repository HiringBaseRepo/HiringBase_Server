"""Soft Skill NLP Scorer — Layer 2 NLP Engine.

Analyzes text to extract soft skill signals:
- Communication
- Leadership
- Teamwork
- Problem Solving
- Initiative / Proactive

Approach: Lightweight rule-based keyword classifier.
Does NOT require LLM. Output: score 0-100 per dimension.
"""
from __future__ import annotations

import re
from typing import Dict, List

import structlog

log = structlog.get_logger(__name__)

# --- Keyword dictionaries per dimension ---

_COMMUNICATION_KEYWORDS: List[str] = [
    "komunikasi", "communication", "presentasi", "presentation",
    "public speaking", "negosiasi", "negotiation", "laporan", "report",
    "briefing", "koordinasi", "koordinator", "facilitator", "fasilitator",
    "client facing", "customer facing", "written", "verbal", "eloquent",
    "articulate", "kolaboratif", "proposal", "pitching",
]

_LEADERSHIP_KEYWORDS: List[str] = [
    "kepemimpinan", "leadership", "team lead", "pemimpin", "memimpin",
    "lead", "led", "supervised", "supervisi", "mentoring", "mentor",
    "coaching", "coach", "managed", "manage", "manajer", "direktur",
    "koordinasi tim", "decision making", "initiative", "inisiatif",
    "memotivasi", "motivating", "delegasi", "delegation", "tanggung jawab",
]

_TEAMWORK_KEYWORDS: List[str] = [
    "teamwork", "kerjasama", "team player", "kolaborasi", "collaboration",
    "bersama", "together", "cross-functional", "lintas departemen",
    "koordinasi", "scrum", "agile", "sprint", "bekerja sama", "gotong royong",
    "interdepartemen", "tim", "group", "divisional",
]

_PROBLEM_SOLVING_KEYWORDS: List[str] = [
    "problem solving", "pemecahan masalah", "analitis", "analytical",
    "troubleshoot", "debugging", "root cause", "solusi", "solution",
    "optimasi", "optimization", "improve", "peningkatan", "efisiensi",
    "kreativitas", "creative", "inovatif", "innovative", "research",
    "riset", "analisis", "analysis", "evaluasi", "evaluation",
]

_INITIATIVE_KEYWORDS: List[str] = [
    "inisiatif", "initiative", "proaktif", "proactive", "mandiri",
    "self-starter", "independent", "inovasi", "innovation", "improvement",
    "continuous improvement", "kaizen", "improvement drive", "motivasi diri",
    "self-motivated", "drive", "passion", "antusias", "enthusiastic",
]


def _count_keyword_matches(text: str, keywords: List[str]) -> int:
    """Count how many keywords are found in the text."""
    text_lower = text.lower()
    count = 0
    for kw in keywords:
        # Use word boundary if possible
        try:
            if re.search(r"\b" + re.escape(kw) + r"\b", text_lower):
                count += 1
        except re.error:
            if kw in text_lower:
                count += 1
    return count


def _keyword_count_to_score(count: int, max_keywords: int = 5) -> float:
    """Convert keyword match count to score 0-100."""
    if count <= 0:
        return 20.0  # minimum score — cannot be 0 only from keywords
    ratio = min(count / max_keywords, 1.0)
    # Scale to 40-100 range (keywords alone are not enough for full score)
    return round(40.0 + ratio * 60.0, 1)


from app.core.cache.service import cache_service

async def score_soft_skills(text: str, force_fallback: bool = False) -> Dict[str, float]:
    """Analyze text and return soft skill scores per dimension using LLM with keyword fallback.

    Args:
        text: Raw text (from OCR or parsing)
        force_fallback: If True, uses keyword-based scoring only.

    Returns:
        Dict with scores per dimension (0-100) and composite_score
    """
    if not text or len(text.strip()) < 50:
        log.warning("Soft skill scoring: text too short or empty")
        return {
            "communication": 30.0,
            "leadership": 30.0,
            "teamwork": 30.0,
            "problem_solving": 30.0,
            "initiative": 30.0,
            "composite_score": 30.0,
        }

    # Check Cache first
    # Only cache if text is substantial and LLM is enabled
    if not force_fallback and len(text.strip()) > 200:
        cached_scores = await cache_service.get("soft_skills", text)
        if cached_scores:
            log.info("Soft skill score cache hit")
            return cached_scores


    # Keyword-based baseline
    comm_count = _count_keyword_matches(text, _COMMUNICATION_KEYWORDS)
    lead_count = _count_keyword_matches(text, _LEADERSHIP_KEYWORDS)
    team_count = _count_keyword_matches(text, _TEAMWORK_KEYWORDS)
    prob_count = _count_keyword_matches(text, _PROBLEM_SOLVING_KEYWORDS)
    init_count = _count_keyword_matches(text, _INITIATIVE_KEYWORDS)

    baseline_scores = {
        "communication": _keyword_count_to_score(comm_count),
        "leadership": _keyword_count_to_score(lead_count),
        "teamwork": _keyword_count_to_score(team_count),
        "problem_solving": _keyword_count_to_score(prob_count),
        "initiative": _keyword_count_to_score(init_count),
    }

    # LLM Enhancement
    from app.ai.llm.client import call_llm
    import json

    if not force_fallback and len(text.strip()) > 200:
        prompt = f"""Analisis soft skill kandidat berdasarkan teks berikut:
---
{text[:3000]}
---

Berikan skor 0-100 untuk dimensi berikut:
1. communication
2. leadership
3. teamwork
4. problem_solving
5. initiative

Kembalikan HANYA objek JSON dengan kunci tersebut.
Contoh: {{"communication": 85, "leadership": 70, ...}}
"""
        try:
            llm_res = await call_llm(prompt, max_tokens=150)
            if llm_res:
                # Find JSON block if LLM added fluff
                start = llm_res.find("{")
                end = llm_res.rfind("}") + 1
                if start != -1 and end != -1:
                    llm_scores = json.loads(llm_res[start:end])
                    # Blend with baseline (LLM 70%, Keywords 30%)
                    for k in baseline_scores:
                        if k in llm_scores:
                            baseline_scores[k] = round(
                                (float(llm_scores[k]) * 0.7) + (baseline_scores[k] * 0.3), 1
                            )
        except Exception as exc:
            log.warning("LLM soft skill scoring failed, using keyword baseline", error=str(exc))

    # Composite: average of all dimensions
    baseline_scores["composite_score"] = round(
        sum(baseline_scores[k] for k in ["communication", "leadership", "teamwork", "problem_solving", "initiative"]) / 5,
        1,
    )

    log.debug("Soft skill scores computed", **baseline_scores)
    
    # Store in cache if LLM was used
    if not force_fallback and len(text.strip()) > 200:
        await cache_service.set("soft_skills", text, baseline_scores, expire=86400)

    return baseline_scores

