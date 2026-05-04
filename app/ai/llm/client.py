"""LLM client for explanation and summarization using Groq."""
from typing import Optional, Dict, Any
import httpx
import structlog
from app.core.config import settings

log = structlog.get_logger(__name__)


async def call_llm(prompt: str, max_tokens: int = 512) -> Optional[str]:
    """Call Groq API (OpenAI compatible)."""
    if not settings.GROQ_API_KEY:
        log.warning("GROQ_API_KEY not configured, LLM calls disabled")
        return None

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.GROQ_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                    "temperature": 0.7
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            else:
                log.error("Groq API error in call_llm", status_code=resp.status_code, body=resp.text)
    except Exception as exc:
        log.error("LLM call failed", error=str(exc))

    return None


async def generate_llm_explanation(candidate_summary: Dict[str, Any]) -> Optional[str]:
    prompt = f"""Summarize this candidate profile for an HR reviewer in 2-3 sentences in Indonesian language.
Candidate skills: {', '.join(candidate_summary.get('skills', []))}
Experience years: {candidate_summary.get('total_years_experience', 0)}
Education: {candidate_summary.get('education', [])}
Score: {candidate_summary.get('final_score', 0)}
"""
    return await call_llm(prompt)
