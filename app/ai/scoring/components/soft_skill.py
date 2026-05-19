"""Soft skill component scoring."""

from typing import Any

from app.shared.constants.scoring import (
    DEFAULT_COMPONENT_RUBRICS,
    anchored_rating_to_score,
)
from app.ai.scoring.utils import safe_rating_from_score


def build_soft_skill_component(
    soft_skill_payload: dict[str, Any],
    text: str,
    text_answer_count: int,
) -> dict[str, Any]:
    composite_score = float(soft_skill_payload.get("composite_score", 0.0))
    text_length = len(text.strip())
    evidence_quality = 100.0
    if text_answer_count <= 1:
        evidence_quality = 50.0
    elif text_answer_count == 2:
        evidence_quality = 70.0
    if text_length < 120:
        evidence_quality = min(evidence_quality, 50.0)
    elif text_length < 250:
        evidence_quality = min(evidence_quality, 70.0)

    raw_score = (composite_score * 0.7) + (evidence_quality * 0.3)
    rating = safe_rating_from_score(raw_score)
    return {
        "score": anchored_rating_to_score(rating),
        "rating": rating,
        "rubric": DEFAULT_COMPONENT_RUBRICS["soft_skill"][rating],
        "raw_score": round(raw_score, 2),
        "confidence": 0.8 if text_length >= 120 else 0.6,
        "evidence": {
            "dimensions": {
                "communication": soft_skill_payload.get("communication"),
                "leadership": soft_skill_payload.get("leadership"),
                "teamwork": soft_skill_payload.get("teamwork"),
                "problem_solving": soft_skill_payload.get("problem_solving"),
                "initiative": soft_skill_payload.get("initiative"),
            },
            "text_answer_count": text_answer_count,
            "text_length": text_length,
            "evidence_quality": round(evidence_quality, 2),
        },
    }
