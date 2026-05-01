"""Lightweight NLP utilities."""
from typing import List, Dict


def tokenize_text(text: str) -> List[str]:
    return text.lower().split()


def extract_entities(text: str) -> Dict[str, List[str]]:
    """Basic entity extraction using regex patterns."""
    import re
    entities = {
        "emails": re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text),
        "phones": re.findall(r"[+]?[0-9\s\-()]{7,20}", text),
        "urls": re.findall(r"https?://[^\s]+", text),
    }
    return entities
