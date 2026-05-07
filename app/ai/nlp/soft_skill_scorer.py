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


def score_soft_skills(text: str) -> Dict[str, float]:
    """Analyze text and return soft skill scores per dimension.

    Args:
        text: Raw text (from OCR or parsing)

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

    comm_count = _count_keyword_matches(text, _COMMUNICATION_KEYWORDS)
    lead_count = _count_keyword_matches(text, _LEADERSHIP_KEYWORDS)
    team_count = _count_keyword_matches(text, _TEAMWORK_KEYWORDS)
    prob_count = _count_keyword_matches(text, _PROBLEM_SOLVING_KEYWORDS)
    init_count = _count_keyword_matches(text, _INITIATIVE_KEYWORDS)

    scores = {
        "communication": _keyword_count_to_score(comm_count),
        "leadership": _keyword_count_to_score(lead_count),
        "teamwork": _keyword_count_to_score(team_count),
        "problem_solving": _keyword_count_to_score(prob_count),
        "initiative": _keyword_count_to_score(init_count),
    }

    # Composite: average of all dimensions
    scores["composite_score"] = round(
        sum(scores[k] for k in ["communication", "leadership", "teamwork", "problem_solving", "initiative"]) / 5,
        1,
    )

    log.debug("Soft skill scores computed", **scores)
    return scores
