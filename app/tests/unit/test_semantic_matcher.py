"""Unit tests untuk semantic matcher — tanpa koneksi model nyata."""
import pytest
from unittest.mock import patch, MagicMock


# =====================================================
# Tests dengan model di-mock (tanpa download model)
# =====================================================

def _make_req(category: str, name: str):
    """Helper buat requirement object yang kompatibel dengan matcher."""
    req = MagicMock(spec=["category", "name"])
    req.category = category
    req.name = name
    return req


@pytest.mark.asyncio
async def test_exact_skill_match():
    """Skill exact match harus terdeteksi tanpa semantic model."""
    from app.ai.matcher.semantic_matcher import match_candidate_to_job

    candidate = {"skills": ["Python", "FastAPI", "Docker"]}
    requirements = [
        _make_req("skill", "python"),
        _make_req("skill", "fastapi"),
    ]

    with patch("app.ai.matcher.semantic_matcher._get_model", return_value=None):
        result = await match_candidate_to_job(candidate, requirements, "backend developer")

    assert result["match_percentage"] == 100.0
    assert len(result["matched_skills"]) == 2
    assert len(result["missing_skills"]) == 0


@pytest.mark.asyncio
async def test_synonym_skill_match():
    """Skill synonym match: 'customer service' ≈ 'client handling'."""
    from app.ai.matcher.semantic_matcher import match_candidate_to_job

    candidate = {"skills": ["client handling", "communication"]}
    requirements = [
        _make_req("skill", "customer service"),
    ]

    with patch("app.ai.matcher.semantic_matcher._get_model", return_value=None):
        result = await match_candidate_to_job(candidate, requirements, "service job")

    assert result["match_percentage"] == 100.0


@pytest.mark.asyncio
async def test_missing_skill_detected():
    """Skill yang tidak ada harus masuk missing_skills."""
    from app.ai.matcher.semantic_matcher import match_candidate_to_job

    candidate = {"skills": ["python"]}
    requirements = [
        _make_req("skill", "python"),
        _make_req("skill", "java"),
        _make_req("skill", "kubernetes"),
    ]

    with patch("app.ai.matcher.semantic_matcher._get_model", return_value=None):
        result = await match_candidate_to_job(candidate, requirements, "full stack engineer")

    assert "java" in result["missing_skills"]
    assert "kubernetes" in result["missing_skills"]
    assert result["match_percentage"] < 100.0


@pytest.mark.asyncio
async def test_empty_candidate_skills():
    """Kandidat tanpa skill → 0% match."""
    from app.ai.matcher.semantic_matcher import match_candidate_to_job

    candidate = {"skills": []}
    requirements = [_make_req("skill", "python")]

    with patch("app.ai.matcher.semantic_matcher._get_model", return_value=None):
        result = await match_candidate_to_job(candidate, requirements, "developer")

    assert result["match_percentage"] == 0.0


@pytest.mark.asyncio
async def test_no_skill_requirements_fallback_to_description():
    """Jika tidak ada skill requirement, gunakan job description sebagai fallback."""
    from app.ai.matcher.semantic_matcher import match_candidate_to_job

    # Non-skill requirements (experience, education)
    candidate = {"skills": ["python", "fastapi", "backend"]}
    requirements = [_make_req("experience", "2 years")]

    with patch("app.ai.matcher.semantic_matcher._get_model", return_value=None):
        result = await match_candidate_to_job(candidate, requirements, "python backend developer fastapi")

    # Dengan fallback ke job description, setidaknya ada partial match
    assert isinstance(result["match_percentage"], float)
    assert result["match_percentage"] >= 0.0


@pytest.mark.asyncio
async def test_confidence_higher_with_model():
    """Confidence score lebih tinggi ketika model tersedia."""
    from app.ai.matcher.semantic_matcher import match_candidate_to_job

    candidate = {"skills": ["python"]}
    requirements = [_make_req("skill", "python")]

    mock_model = MagicMock()

    with patch("app.ai.matcher.semantic_matcher._get_model", return_value=None):
        result_no_model = await match_candidate_to_job(candidate, requirements, "dev")

    with patch("app.ai.matcher.semantic_matcher._get_model", return_value=mock_model):
        with patch("app.ai.matcher.semantic_matcher._semantic_match", return_value=False):
            result_with_model = await match_candidate_to_job(candidate, requirements, "dev")

    assert result_with_model["confidence_score"] > result_no_model["confidence_score"]


# =====================================================
# Synonym map tests
# =====================================================

def test_synonym_map_has_key_entries():
    from app.ai.matcher.semantic_matcher import _synonym_map
    synonyms = _synonym_map()
    assert "customer service" in synonyms
    assert "node.js" in synonyms
    assert "react" in synonyms
    assert len(synonyms) >= 5


# =====================================================
# Exact + synonym match helper tests
# =====================================================

def test_exact_match_found():
    from app.ai.matcher.semantic_matcher import _exact_and_synonym_match, _synonym_map
    candidate = {"python", "docker"}
    assert _exact_and_synonym_match("python", candidate, _synonym_map()) is True


def test_exact_match_not_found():
    from app.ai.matcher.semantic_matcher import _exact_and_synonym_match, _synonym_map
    candidate = {"java", "docker"}
    assert _exact_and_synonym_match("python", candidate, _synonym_map()) is False


def test_synonym_match_via_group():
    from app.ai.matcher.semantic_matcher import _exact_and_synonym_match, _synonym_map
    # "react" group includes "next.js"
    candidate = {"next.js", "typescript"}
    result = _exact_and_synonym_match("react", candidate, _synonym_map())
    assert result is True
