"""Administrative component scoring."""

from typing import Any

from app.shared.constants.scoring import (
    DEFAULT_COMPONENT_RUBRICS,
    anchored_rating_to_score,
)
from app.ai.scoring.utils import safe_rating_from_score


def build_administrative_component(
    document_count: int,
    doc_validation_flags: list[dict[str, Any]],
) -> dict[str, Any]:
    if document_count <= 0:
        raw_score = 20.0
    elif any(flag.get("risk_level") == "high" for flag in doc_validation_flags if isinstance(flag, dict)):
        raw_score = 20.0
    elif doc_validation_flags:
        raw_score = 60.0
    else:
        raw_score = 100.0

    rating = safe_rating_from_score(raw_score)
    return {
        "score": anchored_rating_to_score(rating),
        "rating": rating,
        "rubric": DEFAULT_COMPONENT_RUBRICS["administrative"][rating],
        "raw_score": round(raw_score, 2),
        "confidence": 0.9,
        "evidence": {
            "document_count": document_count,
            "validation_flags": doc_validation_flags,
        },
    }
