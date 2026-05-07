"""Unit tests for AI explanation logic."""

import pytest
from unittest.mock import patch, MagicMock
from app.ai.explanation.generator import generate_explanation

@pytest.mark.asyncio
async def test_explanation_recommends_interview_on_high_score():
    """Penjelasan harus menyarankan interview jika skor tinggi."""
    with patch("app.ai.explanation.generator.call_llm") as mock_llm:
        mock_llm.side_effect = Exception("LLM Error")
        
        explanation = await generate_explanation(
            match_result={"matched_skills": ["Python", "FastAPI"], "missing_skills": []},
            exp_score=85.5,
            edu_score=80.0,
            portfolio_score=70.0,
            soft_skill_score=80.0,
            admin_score=100.0,
            final_score=85.5,
            red_flags={"red_flags": []}
        )
        
        assert "Direkomendasikan untuk tahap wawancara" in explanation
        assert "Python" in explanation

@pytest.mark.asyncio
async def test_explanation_warns_on_low_score():
    """Penjelasan harus memberikan peringatan jika skor rendah."""
    with patch("app.ai.explanation.generator.call_llm") as mock_llm:
        mock_llm.side_effect = Exception("LLM Error")
        
        explanation = await generate_explanation(
            match_result={"matched_skills": ["Excel"], "missing_skills": ["Python"]},
            exp_score=40.0,
            edu_score=50.0,
            portfolio_score=30.0,
            soft_skill_score=50.0,
            admin_score=100.0,
            final_score=45.0,
            red_flags={"red_flags": []}
        )
        
        assert "Memerlukan tinjauan manual HR" in explanation

@pytest.mark.asyncio
async def test_explanation_mentions_document_anomalies():
    """Penjelasan harus menyebutkan anomali dokumen jika ada red flags terkait admin."""
    with patch("app.ai.explanation.generator.call_llm") as mock_llm:
        mock_llm.side_effect = Exception("LLM Error")
        
        explanation = await generate_explanation(
            match_result={"matched_skills": ["Java"], "missing_skills": []},
            exp_score=70.0,
            edu_score=70.0,
            portfolio_score=70.0,
            soft_skill_score=70.0,
            admin_score=70.0,
            final_score=70.0,
            red_flags={"red_flags": ["Ijazah anomali detected"]}
        )
        
        assert "Ditemukan anomali pada verifikasi dokumen administrasi" in explanation
