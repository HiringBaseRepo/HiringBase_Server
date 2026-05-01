"""Red flag detection engine."""
from typing import Dict, List
import re


def detect_red_flags(parsed_data: Dict, raw_text: str) -> Dict:
    """Detect risk indicators in candidate profile."""
    flags = []
    risk_level = "low"

    # Employment gap
    experiences = parsed_data.get("experiences", [])
    if len(experiences) > 1:
        gaps = []
        for i in range(1, len(experiences)):
            prev_end = experiences[i-1].get("end", 0)
            curr_start = experiences[i].get("start", 0)
            if curr_start - prev_end > 1:
                gaps.append(curr_start - prev_end)
        if any(g > 2 for g in gaps):
            flags.append("Large employment gap detected")

    # Job hopping
    if len(experiences) >= 4:
        avg_years = sum(e.get("years", 0) for e in experiences) / len(experiences)
        if avg_years < 1:
            flags.append("Potential job hopping pattern")

    # Too many typos
    words = raw_text.split()
    if len(words) > 20:
        typo_patterns = re.findall(r"\b(teh|adn|hte|recieve|seperate)\b", raw_text.lower())
        if len(typo_patterns) > 3:
            flags.append("High typo rate in document")

    # Salary unrealistic placeholder check
    salary_matches = re.findall(r"\b(100\s*juta|1\s*miliar)\b", raw_text.lower())
    if salary_matches:
        flags.append("Unrealistic salary expectation")

    # Determine risk
    if len(flags) >= 3:
        risk_level = "high"
    elif len(flags) >= 1:
        risk_level = "medium"

    return {
        "red_flags": flags,
        "risk_level": risk_level,
    }
