"""Unit tests untuk AI scoring dan parsing logic."""
import pytest
from app.ai.parser.resume_parser import parse_resume_text
from app.ai.redflag.detector import detect_red_flags
from app.ai.nlp.soft_skill_scorer import score_soft_skills
from app.shared.constants.scoring import EDUCATION_RANK


# =====================================================
# Resume Parser Tests
# =====================================================

SAMPLE_CV_TEXT = """
John Doe
johndoe@email.com
+62 812-3456-7890

EDUCATION
S1 Teknik Informatika - Universitas Indonesia (2018-2022)

EXPERIENCE
Software Engineer - PT Teknologi Maju
2022 - present

Junior Developer - Startup ABC
2021 - 2022

SKILLS
Python, FastAPI, PostgreSQL, Docker, React, Git, CI/CD

PORTFOLIO
https://github.com/johndoe
https://portfolio.johndoe.com

CERTIFICATIONS
AWS Certified Developer sertifikasi
"""


def test_parse_resume_extracts_email():
    result = parse_resume_text(SAMPLE_CV_TEXT)
    assert result["email"] == "johndoe@email.com"


def test_parse_resume_extracts_skills():
    result = parse_resume_text(SAMPLE_CV_TEXT)
    skills = result["skills"]
    assert "python" in skills
    assert "docker" in skills
    assert "react" in skills


def test_parse_resume_extracts_education():
    result = parse_resume_text(SAMPLE_CV_TEXT)
    edu = result["education"]
    assert len(edu) > 0
    levels = [e["level"] for e in edu]
    assert "s1" in levels


def test_parse_resume_extracts_experience_years():
    result = parse_resume_text(SAMPLE_CV_TEXT)
    assert result["total_years_experience"] >= 1


def test_parse_resume_extracts_github():
    result = parse_resume_text(SAMPLE_CV_TEXT)
    assert result["github_url"] is not None
    assert "github.com" in result["github_url"]


def test_parse_resume_extracts_certifications():
    result = parse_resume_text(SAMPLE_CV_TEXT)
    assert len(result["certifications"]) > 0


def test_parse_resume_empty_text():
    result = parse_resume_text("")
    assert result["skills"] == []
    assert result["total_years_experience"] == 0


# =====================================================
# Red Flag Detection Tests
# =====================================================

def test_redflag_no_flags_clean_cv():
    parsed = {
        "experiences": [{"start": 2019, "end": 2022, "years": 3}],
    }
    result = detect_red_flags(parsed, "Professional resume text without issues")
    assert result["risk_level"] in ("low", "medium")


def test_redflag_detects_job_hopping():
    parsed = {
        "experiences": [
            {"start": 2019, "end": 2019, "years": 0},
            {"start": 2019, "end": 2020, "years": 1},
            {"start": 2020, "end": 2020, "years": 0},
            {"start": 2020, "end": 2021, "years": 1},
        ],
    }
    result = detect_red_flags(parsed, "sample text " * 10)
    flags = result["red_flags"]
    assert any("hopping" in f.lower() for f in flags)


def test_redflag_detects_employment_gap():
    parsed = {
        "experiences": [
            {"start": 2015, "end": 2017, "years": 2},
            {"start": 2020, "end": 2022, "years": 2},  # 3 year gap
        ],
    }
    result = detect_red_flags(parsed, "sample text " * 10)
    flags = result["red_flags"]
    assert any("gap" in f.lower() for f in flags)


def test_redflag_high_risk_multiple_flags():
    parsed = {
        "experiences": [
            {"start": 2019, "end": 2019, "years": 0},
            {"start": 2019, "end": 2019, "years": 0},
            {"start": 2019, "end": 2019, "years": 0},
            {"start": 2019, "end": 2019, "years": 0},
        ],
    }
    text = "teh adn hte recieve seperate " * 5 + "100 juta salary expected " * 3
    result = detect_red_flags(parsed, text)
    assert result["risk_level"] in ("medium", "high")


# =====================================================
# Soft Skill Scorer Tests
# =====================================================

def test_soft_skill_scorer_communication_keywords():
    text = "Berpengalaman dalam komunikasi dan presentasi kepada stakeholder. Public speaking dan negosiasi kontrak."
    result = score_soft_skills(text)
    assert result["communication"] > 40.0


def test_soft_skill_scorer_leadership_keywords():
    text = "Led a team of 5 developers. Responsible for mentoring junior engineers and decision making."
    result = score_soft_skills(text)
    assert result["leadership"] > 40.0


def test_soft_skill_scorer_teamwork():
    text = "Bekerja dalam tim lintas departemen. Kolaborasi dengan tim marketing dan produk dalam sprint agile."
    result = score_soft_skills(text)
    assert result["teamwork"] > 40.0


def test_soft_skill_scorer_returns_composite():
    text = "Communication teamwork leadership problem solving initiative collaboration"
    result = score_soft_skills(text)
    assert "composite_score" in result
    assert 0 <= result["composite_score"] <= 100


def test_soft_skill_scorer_empty_text():
    result = score_soft_skills("")
    assert result["composite_score"] == 30.0  # default minimum


def test_soft_skill_scorer_short_text():
    result = score_soft_skills("hello")
    assert result["composite_score"] == 30.0  # text too short


# =====================================================
# Education Rank Tests
# =====================================================

def test_education_rank_ordering():
    assert EDUCATION_RANK["s1"] > EDUCATION_RANK["d3"]
    assert EDUCATION_RANK["s2"] > EDUCATION_RANK["s1"]
    assert EDUCATION_RANK["s3"] > EDUCATION_RANK["s2"]
    assert EDUCATION_RANK["sma"] < EDUCATION_RANK["d1"]


# =====================================================
# Screening helper functions Tests
# =====================================================

def test_compare_numeric_operators():
    from app.features.screening.router import _compare_numeric
    assert _compare_numeric(5.0, 3.0, "gt") is True
    assert _compare_numeric(3.0, 5.0, "gt") is False
    assert _compare_numeric(5.0, 5.0, "gte") is True
    assert _compare_numeric(3.0, 5.0, "gte") is False
    assert _compare_numeric(3.0, 5.0, "lt") is True
    assert _compare_numeric(5.0, 5.0, "eq") is True
    assert _compare_numeric(4.0, 5.0, "neq") is True


def test_score_experience_meets_requirement():
    from app.features.screening.router import _score_experience
    assert _score_experience(3, "2") == 100.0


def test_score_experience_below_requirement():
    from app.features.screening.router import _score_experience
    score = _score_experience(1, "2")
    assert score == 50.0


def test_score_experience_no_requirement():
    from app.features.screening.router import _score_experience
    assert _score_experience(0, "0") == 100.0


def test_score_education_meets():
    from app.features.screening.router import _score_education
    edu = [{"level": "s1"}]
    assert _score_education(edu, "s1") == 100.0


def test_score_education_overqualified():
    from app.features.screening.router import _score_education
    edu = [{"level": "s2"}]
    assert _score_education(edu, "s1") == 100.0


def test_score_education_underqualified():
    from app.features.screening.router import _score_education
    edu = [{"level": "d3"}]
    score = _score_education(edu, "s1")
    assert score < 100.0


def test_score_portfolio_full():
    from app.features.screening.router import _score_portfolio
    parsed = {"github_url": "https://github.com/test", "live_project_url": "https://myapp.com"}
    assert _score_portfolio(parsed) == 100.0


def test_score_portfolio_github_only():
    from app.features.screening.router import _score_portfolio
    parsed = {"github_url": "https://github.com/test"}
    assert _score_portfolio(parsed) == 75.0


def test_score_portfolio_empty():
    from app.features.screening.router import _score_portfolio
    assert _score_portfolio({}) == 0.0
