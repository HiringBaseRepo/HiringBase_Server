"""LLM client for explanation and summarization."""
from typing import Optional, Dict, Any
import httpx

from app.core.config import settings


async def call_llm(prompt: str, max_tokens: int = 512) -> Optional[str]:
    """Call LLM API with fallback."""
    if not settings.HF_API_TOKEN:
        return None

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                settings.HF_LLM_API_URL,
                headers={"Authorization": f"Bearer {settings.HF_API_TOKEN}"},
                json={"inputs": prompt, "parameters": {"max_new_tokens": max_tokens, "return_full_text": False}},
            )
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    return data[0].get("generated_text", "")
    except Exception:
        pass

    # Fallback to OpenRouter if configured
    if settings.OPENROUTER_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "meta-llama/llama-3.1-8b-instruct",
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": max_tokens,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data["choices"][0]["message"]["content"]
        except Exception:
            pass

    return None


async def generate_llm_explanation(candidate_summary: Dict[str, Any]) -> Optional[str]:
    prompt = f"""Summarize this candidate profile for an HR reviewer in 2-3 sentences in Indonesian language.
Candidate skills: {', '.join(candidate_summary.get('skills', []))}
Experience years: {candidate_summary.get('total_years_experience', 0)}
Education: {candidate_summary.get('education', [])}
Score: {candidate_summary.get('final_score', 0)}
"""
    return await call_llm(prompt)
