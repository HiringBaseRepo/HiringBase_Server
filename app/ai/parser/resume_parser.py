"""Resume text parser to structured JSON."""
import re
from typing import Dict, Any, List, Optional


def parse_resume_text(text: str) -> Dict[str, Any]:
    """Parse raw resume text into structured candidate data."""
    data = {
        "name": _extract_name(text),
        "email": _extract_email(text),
        "phone": _extract_phone(text),
        "skills": _extract_skills(text),
        "education": _extract_education(text),
        "experiences": _extract_experiences(text),
        "total_years_experience": 0,
        "certifications": _extract_certifications(text),
        "languages": _extract_languages(text),
        "github_url": _extract_url(text, "github"),
        "linkedin_url": _extract_url(text, "linkedin"),
        "portfolio_url": _extract_url(text, "portfolio"),
        "live_project_url": _extract_url(text, "demo") or _extract_url(text, "live"),
    }
    data["total_years_experience"] = _calculate_total_years(data["experiences"])
    return data


def _extract_name(text: str) -> Optional[str]:
    lines = text.strip().split("\n")[:5]
    for line in lines:
        line = line.strip()
        if len(line) > 2 and len(line) < 60 and not any(c in line for c in ["@", "/", "-", "*", "#"]):
            return line
    return None


def _extract_email(text: str) -> Optional[str]:
    match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    return match.group(0) if match else None


def _extract_phone(text: str) -> Optional[str]:
    match = re.search(r"[+]?[0-9\s\-()]{7,20}", text)
    return match.group(0) if match else None


def _extract_skills(text: str) -> List[str]:
    skill_keywords = [
        "python", "javascript", "typescript", "java", "c++", "c#", "go", "rust",
        "react", "vue", "angular", "node.js", "django", "flask", "fastapi",
        "sql", "postgresql", "mysql", "mongodb", "redis", "docker", "kubernetes",
        "aws", "gcp", "azure", "linux", "git", "ci/cd", "agile", "scrum",
        "machine learning", "data science", "nlp", "computer vision", "tensorflow", "pytorch",
        "excel", "word", "powerpoint", "project management", "leadership", "communication",
    ]
    found = []
    lower = text.lower()
    for skill in skill_keywords:
        if skill in lower:
            found.append(skill)
    return found


def _extract_education(text: str) -> List[Dict[str, Any]]:
    education = []
    lines = text.split("\n")
    for line in lines:
        line_lower = line.lower()
        if any(x in line_lower for x in ["s1", "s2", "s3", "d1", "d2", "d3", "sma", "smk", "sarjana", "diploma", "master", "phd"]):
            level = "s1"
            if "s2" in line_lower or "master" in line_lower:
                level = "s2"
            elif "s3" in line_lower or "phd" in line_lower or "doctor" in line_lower:
                level = "s3"
            elif "d3" in line_lower:
                level = "d3"
            elif "d2" in line_lower:
                level = "d2"
            elif "d1" in line_lower:
                level = "d1"
            elif "sma" in line_lower or "smk" in line_lower:
                level = "sma"
            education.append({"level": level, "raw": line.strip()})
    return education


def _extract_experiences(text: str) -> List[Dict[str, Any]]:
    experiences = []
    pattern = re.compile(r"(20\d{2})\s*[-—]\s*(20\d{2}|present|sekarang)", re.IGNORECASE)
    for match in pattern.finditer(text):
        start = int(match.group(1))
        end_str = match.group(2).lower()
        end = 2025 if end_str in ["present", "sekarang", "now"] else int(end_str)
        experiences.append({"start": start, "end": end, "years": max(0, end - start)})
    return experiences


def _calculate_total_years(experiences: List[Dict]) -> int:
    return sum(e["years"] for e in experiences)


def _extract_certifications(text: str) -> List[str]:
    certs = []
    lines = text.split("\n")
    for line in lines:
        if "certif" in line.lower() or "sertif" in line.lower():
            certs.append(line.strip())
    return certs


def _extract_languages(text: str) -> List[str]:
    langs = []
    language_list = ["indonesia", "english", "mandarin", "japanese", "korean", "french", "german", "spanish", "arabic"]
    lower = text.lower()
    for lang in language_list:
        if lang in lower:
            langs.append(lang)
    return langs


def _extract_url(text: str, domain_hint: str) -> Optional[str]:
    pattern = re.compile(r"https?://[^\s]+" + domain_hint + r"[^\s]*", re.IGNORECASE)
    match = pattern.search(text)
    return match.group(0) if match else None
