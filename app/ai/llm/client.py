"""LLM client for explanation and summarization using Groq."""
from typing import Optional, Dict, Any
import httpx
import structlog
from app.core.config import settings

log = structlog.get_logger(__name__)


def get_groq_api_keys() -> list[str]:
    """Return configured Groq keys in fallback order."""
    keys = [settings.GROQ_API_KEY, settings.GROQ_API_KEY_FALLBACK]
    return [key for key in keys if key]


async def post_groq_chat_completion(
    *,
    client: httpx.AsyncClient,
    payload: dict[str, Any],
) -> httpx.Response | None:
    """Call Groq with primary key first, then fallback key on rate limit."""
    keys = get_groq_api_keys()
    if not keys:
        return None

    last_response: httpx.Response | None = None
    for index, api_key in enumerate(keys):
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        last_response = response

        if response.status_code != 429:
            if index > 0 and response.status_code == 200:
                log.warning(
                    "groq_fallback_key_used",
                    fallback_index=index,
                )
            return response

        log.warning(
            "groq_rate_limit_hit",
            fallback_index=index,
        )

    return last_response


async def call_llm(prompt: str, max_tokens: int = 512) -> Optional[str]:
    """Call Groq API (OpenAI compatible)."""
    if not get_groq_api_keys():
        log.warning("GROQ_API_KEY not configured, LLM calls disabled")
        return None

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await post_groq_chat_completion(
                client=client,
                payload={
                    "model": settings.GROQ_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                    "temperature": 0.7,
                },
            )
            if resp is None:
                return None
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
