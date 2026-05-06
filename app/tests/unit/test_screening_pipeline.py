"""Unit tests for process_screening orchestrator.

Tests the full AI pipeline logic in isolation using mocked DB and services.
Covers: doc validation, knockout rules, scoring, status transitions.

Catatan teknis:
- process_screening melakukan lazy import `from app.core.database.session import get_session`
  di dalam fungsi body, sehingga kita WAJIB patch `app.core.database.session.get_session`
  agar mock ter-apply saat fungsi dijalankan.
"""

import pytest
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

from app.shared.enums.application_status import ApplicationStatus
from app.shared.enums.document_type import DocumentType
from app.shared.constants.scoring import MINIMUM_PASS_SCORE


# =============================================================================
# Helpers / Mock Factories
# =============================================================================

def _make_application(
    app_id: int = 1,
    job_id: int = 10,
    applicant_id: int = 100,
    status: ApplicationStatus = ApplicationStatus.AI_PROCESSING,
):
    app = MagicMock()
    app.id = app_id
    app.job_id = job_id
    app.applicant_id = applicant_id
    app.status = status
    app.applicant = MagicMock()
    app.applicant.full_name = "John Doe"
    app.applicant.email = "john@example.com"
    return app


def _make_job(job_id: int = 10, description: str = "Python developer role"):
    job = MagicMock()
    job.id = job_id
    job.description = description
    return job


def _make_doc(doc_type: DocumentType, url: str = "https://r2.example.com/doc.pdf"):
    doc = MagicMock()
    doc.document_type = doc_type
    doc.file_url = url
    return doc


def _make_answer(field_key: str, value_text: str = None, value_number: float = None):
    ans = MagicMock()
    ans.field_key = field_key
    ans.value_text = value_text
    ans.value_number = value_number
    return ans


def _make_template(
    skill=40, exp=20, edu=10, portfolio=10, soft=10, admin=10
):
    t = MagicMock()
    t.skill_match_weight = skill
    t.experience_weight = exp
    t.education_weight = edu
    t.portfolio_weight = portfolio
    t.soft_skill_weight = soft
    t.administrative_weight = admin
    return t


def _mock_session_ctx(mock_db: AsyncMock):
    """Buat async context manager mock untuk get_session."""
    @asynccontextmanager
    async def _ctx():
        yield mock_db
    return _ctx


# =============================================================================
# Test: Missing Documents → DOC_FAILED
# =============================================================================

@pytest.mark.asyncio
async def test_process_screening_doc_failed_when_missing_ijazah():
    """Screening harus set DOC_FAILED jika Ijazah tidak ada."""
    app = _make_application()
    job = _make_job()
    docs = [_make_doc(DocumentType.KTP)]  # Hanya KTP

    mock_db = AsyncMock()
    ktp_rule = MagicMock()
    ktp_rule.rule_type = "document"
    ktp_rule.target_value = "KTP"
    ijazah_rule = MagicMock()
    ijazah_rule.rule_type = "document"
    ijazah_rule.target_value = "IJAZAH"

    with patch("app.core.database.session.get_session", _mock_session_ctx(mock_db)), \
         patch("app.features.screening.services.service.get_application_by_id", AsyncMock(return_value=app)), \
         patch("app.features.screening.services.service.get_job_by_id", AsyncMock(return_value=job)), \
         patch("app.features.screening.services.service.get_documents_by_application_id", AsyncMock(return_value=docs)), \
         patch("app.features.screening.services.service.get_active_knockout_rules", AsyncMock(return_value=[ktp_rule, ijazah_rule])), \
         patch("app.features.screening.services.service.add_status_log", AsyncMock()):

        from app.features.screening.services.service import process_screening
        await process_screening(1, company_id=10)

    assert app.status == ApplicationStatus.DOC_FAILED


@pytest.mark.asyncio
async def test_process_screening_doc_failed_when_missing_ktp():
    """Screening harus set DOC_FAILED jika KTP tidak ada."""
    app = _make_application()
    job = _make_job()
    docs = [_make_doc(DocumentType.IJAZAH)]  # Hanya Ijazah

    mock_db = AsyncMock()
    ktp_rule = MagicMock()
    ktp_rule.rule_type = "document"
    ktp_rule.target_value = "KTP"

    with patch("app.core.database.session.get_session", _mock_session_ctx(mock_db)), \
         patch("app.features.screening.services.service.get_application_by_id", AsyncMock(return_value=app)), \
         patch("app.features.screening.services.service.get_job_by_id", AsyncMock(return_value=job)), \
         patch("app.features.screening.services.service.get_documents_by_application_id", AsyncMock(return_value=docs)), \
         patch("app.features.screening.services.service.get_active_knockout_rules", AsyncMock(return_value=[ktp_rule])), \
         patch("app.features.screening.services.service.add_status_log", AsyncMock()):

        from app.features.screening.services.service import process_screening
        await process_screening(1, company_id=10)

    assert app.status == ApplicationStatus.DOC_FAILED


@pytest.mark.asyncio
async def test_process_screening_doc_failed_no_documents():
    """Screening harus set DOC_FAILED jika tidak ada dokumen sama sekali."""
    app = _make_application()
    job = _make_job()
    mock_db = AsyncMock()

    ktp_rule = MagicMock()
    ktp_rule.rule_type = "document"
    ktp_rule.target_value = "KTP"

    with patch("app.core.database.session.get_session", _mock_session_ctx(mock_db)), \
         patch("app.features.screening.services.service.get_application_by_id", AsyncMock(return_value=app)), \
         patch("app.features.screening.services.service.get_job_by_id", AsyncMock(return_value=job)), \
         patch("app.features.screening.services.service.get_documents_by_application_id", AsyncMock(return_value=[])), \
         patch("app.features.screening.services.service.get_active_knockout_rules", AsyncMock(return_value=[ktp_rule])), \
         patch("app.features.screening.services.service.add_status_log", AsyncMock()):

        from app.features.screening.services.service import process_screening
        await process_screening(1, company_id=10)

    assert app.status == ApplicationStatus.DOC_FAILED


# =============================================================================
# Test: Application / Job tidak ditemukan → early return
# =============================================================================

@pytest.mark.asyncio
async def test_process_screening_returns_early_if_application_not_found():
    """Screening harus berhenti tanpa error jika application tidak ditemukan."""
    mock_db = AsyncMock()

    with patch("app.core.database.session.get_session", _mock_session_ctx(mock_db)), \
         patch("app.features.screening.services.service.get_application_by_id", AsyncMock(return_value=None)):

        from app.features.screening.services.service import process_screening
        # Tidak boleh raise exception
        await process_screening(999, company_id=10)


@pytest.mark.asyncio
async def test_process_screening_returns_early_if_job_not_found():
    """Screening harus berhenti tanpa error jika job tidak ditemukan."""
    app = _make_application()
    mock_db = AsyncMock()

    with patch("app.core.database.session.get_session", _mock_session_ctx(mock_db)), \
         patch("app.features.screening.services.service.get_application_by_id", AsyncMock(return_value=app)), \
         patch("app.features.screening.services.service.get_job_by_id", AsyncMock(return_value=None)):

        from app.features.screening.services.service import process_screening
        await process_screening(1, company_id=10)


# =============================================================================
# Test: Knockout Rules → KNOCKOUT
# =============================================================================

@pytest.mark.asyncio
async def test_process_screening_knockout_when_rule_fails():
    """Screening harus set KNOCKOUT jika ada knockout rule yang gagal."""
    app = _make_application()
    job = _make_job()
    docs = [_make_doc(DocumentType.KTP), _make_doc(DocumentType.IJAZAH)]
    rule = MagicMock()
    rule.rule_name = "Min Experience 3 Years"
    answers = [_make_answer("experience_years", value_text="1")]
    mock_db = AsyncMock()

    with patch("app.core.database.session.get_session", _mock_session_ctx(mock_db)), \
         patch("app.features.screening.services.service.get_application_by_id", AsyncMock(return_value=app)), \
         patch("app.features.screening.services.service.get_job_by_id", AsyncMock(return_value=job)), \
         patch("app.features.screening.services.service.get_documents_by_application_id", AsyncMock(return_value=docs)), \
         patch("app.features.screening.services.service.get_active_knockout_rules", AsyncMock(return_value=[rule])), \
         patch("app.features.screening.services.service.get_answers_by_application_id", AsyncMock(return_value=answers)), \
         patch("app.features.screening.services.service.evaluate_knockout_rule", return_value=False), \
         patch("app.features.screening.services.service.add_status_log", AsyncMock()), \
         patch("app.features.screening.services.service.run_document_semantic_check", AsyncMock(return_value=[])):

        from app.features.screening.services.service import process_screening
        await process_screening(1, company_id=10)

    assert app.status == ApplicationStatus.KNOCKOUT


@pytest.mark.asyncio
async def test_process_screening_passes_knockout_when_all_rules_pass():
    """Screening melanjutkan ke scoring jika semua knockout rules lulus."""
    app = _make_application()
    job = _make_job()
    docs = [_make_doc(DocumentType.KTP), _make_doc(DocumentType.IJAZAH)]
    rule = MagicMock()
    rule.rule_name = "Min Experience"
    answers = [
        _make_answer("skills", value_text="Python, FastAPI"),
        _make_answer("experience_years", value_text="5"),
        _make_answer("education_level", value_text="s1"),
    ]
    template = _make_template()
    mock_db = AsyncMock()
    saved_scores = []

    async def capture_save(db, score):
        saved_scores.append(score)

    with patch("app.core.database.session.get_session", _mock_session_ctx(mock_db)), \
         patch("app.features.screening.services.service.get_application_by_id", AsyncMock(return_value=app)), \
         patch("app.features.screening.services.service.get_job_by_id", AsyncMock(return_value=job)), \
         patch("app.features.screening.services.service.get_documents_by_application_id", AsyncMock(return_value=docs)), \
         patch("app.features.screening.services.service.get_active_knockout_rules", AsyncMock(return_value=[rule])), \
         patch("app.features.screening.services.service.get_answers_by_application_id", AsyncMock(return_value=answers)), \
         patch("app.features.screening.services.service.evaluate_knockout_rule", return_value=True), \
         patch("app.features.screening.services.service.run_document_semantic_check", AsyncMock(return_value=[])), \
         patch("app.features.screening.services.service.get_scoring_template_by_job_id", AsyncMock(return_value=template)), \
         patch("app.features.screening.services.service.get_requirements_by_job_id", AsyncMock(return_value=[])), \
         patch("app.features.screening.services.service.match_candidate_to_job", AsyncMock(return_value={"match_percentage": 80.0, "matched": [], "missing": []})), \
         patch("app.features.screening.services.service.save_candidate_score", AsyncMock(side_effect=capture_save)), \
         patch("app.features.screening.services.service.add_status_log", AsyncMock()):

        from app.features.screening.services.service import process_screening
        await process_screening(1, company_id=10)

    assert len(saved_scores) == 1
    assert app.status in (ApplicationStatus.AI_PASSED, ApplicationStatus.UNDER_REVIEW)


# =============================================================================
# Test: Status Transitions berdasarkan skor
# =============================================================================

@pytest.mark.asyncio
async def test_process_screening_ai_passed_when_score_above_threshold():
    """Status harus AI_PASSED jika final_score >= MINIMUM_PASS_SCORE."""
    app = _make_application()
    job = _make_job()
    docs = [_make_doc(DocumentType.KTP), _make_doc(DocumentType.IJAZAH)]
    answers = [
        _make_answer("skills", value_text="Python, FastAPI, SQL, Docker"),
        _make_answer("experience_years", value_text="10"),
        _make_answer("education_level", value_text="s2"),
        _make_answer("github_url", value_text="https://github.com/johndoe"),
    ]
    # Skill 100% → final = match_percentage * 1.0
    template = _make_template(skill=100, exp=0, edu=0, portfolio=0, soft=0, admin=0)
    mock_db = AsyncMock()

    with patch("app.core.database.session.get_session", _mock_session_ctx(mock_db)), \
         patch("app.features.screening.services.service.get_application_by_id", AsyncMock(return_value=app)), \
         patch("app.features.screening.services.service.get_job_by_id", AsyncMock(return_value=job)), \
         patch("app.features.screening.services.service.get_documents_by_application_id", AsyncMock(return_value=docs)), \
         patch("app.features.screening.services.service.get_active_knockout_rules", AsyncMock(return_value=[])), \
         patch("app.features.screening.services.service.get_answers_by_application_id", AsyncMock(return_value=answers)), \
         patch("app.features.screening.services.service.run_document_semantic_check", AsyncMock(return_value=[])), \
         patch("app.features.screening.services.service.get_scoring_template_by_job_id", AsyncMock(return_value=template)), \
         patch("app.features.screening.services.service.get_requirements_by_job_id", AsyncMock(return_value=[])), \
         patch("app.features.screening.services.service.match_candidate_to_job",
               AsyncMock(return_value={"match_percentage": 90.0, "matched": [], "missing": []})), \
         patch("app.features.screening.services.service.save_candidate_score", AsyncMock()), \
         patch("app.features.screening.services.service.add_status_log", AsyncMock()):

        from app.features.screening.services.service import process_screening
        await process_screening(1, company_id=10)

    assert app.status == ApplicationStatus.AI_PASSED, (
        f"Expected AI_PASSED for score ~90, MINIMUM_PASS_SCORE={MINIMUM_PASS_SCORE}"
    )


@pytest.mark.asyncio
async def test_process_screening_under_review_when_score_below_threshold():
    """Status harus UNDER_REVIEW jika final_score < MINIMUM_PASS_SCORE."""
    app = _make_application()
    job = _make_job()
    docs = [_make_doc(DocumentType.KTP), _make_doc(DocumentType.IJAZAH)]
    answers = [_make_answer("skills", value_text="Basic Excel")]
    template = _make_template(skill=100, exp=0, edu=0, portfolio=0, soft=0, admin=0)
    mock_db = AsyncMock()

    with patch("app.core.database.session.get_session", _mock_session_ctx(mock_db)), \
         patch("app.features.screening.services.service.get_application_by_id", AsyncMock(return_value=app)), \
         patch("app.features.screening.services.service.get_job_by_id", AsyncMock(return_value=job)), \
         patch("app.features.screening.services.service.get_documents_by_application_id", AsyncMock(return_value=docs)), \
         patch("app.features.screening.services.service.get_active_knockout_rules", AsyncMock(return_value=[])), \
         patch("app.features.screening.services.service.get_answers_by_application_id", AsyncMock(return_value=answers)), \
         patch("app.features.screening.services.service.run_document_semantic_check", AsyncMock(return_value=[])), \
         patch("app.features.screening.services.service.get_scoring_template_by_job_id", AsyncMock(return_value=template)), \
         patch("app.features.screening.services.service.get_requirements_by_job_id", AsyncMock(return_value=[])), \
         patch("app.features.screening.services.service.match_candidate_to_job",
               AsyncMock(return_value={"match_percentage": 10.0, "matched": [], "missing": []})), \
         patch("app.features.screening.services.service.save_candidate_score", AsyncMock()), \
         patch("app.features.screening.services.service.add_status_log", AsyncMock()):

        from app.features.screening.services.service import process_screening
        await process_screening(1, company_id=10)

    assert app.status == ApplicationStatus.UNDER_REVIEW


# =============================================================================
# Test: Red Flags dari validasi dokumen
# =============================================================================

@pytest.mark.asyncio
async def test_process_screening_doc_anomaly_sets_high_risk():
    """Jika dokumen mengandung anomali, risk_level harus 'high' dan red_flags berisi peringatan."""
    app = _make_application()
    job = _make_job()
    docs = [_make_doc(DocumentType.KTP), _make_doc(DocumentType.IJAZAH)]
    answers = [_make_answer("skills", value_text="Python")]
    template = _make_template()
    mock_db = AsyncMock()
    captured_scores = []

    async def capture_save(db, score):
        captured_scores.append(score)

    doc_flags = ["Peringatan KTP: Nama tidak cocok dengan data pelamar"]

    with patch("app.core.database.session.get_session", _mock_session_ctx(mock_db)), \
         patch("app.features.screening.services.service.get_application_by_id", AsyncMock(return_value=app)), \
         patch("app.features.screening.services.service.get_job_by_id", AsyncMock(return_value=job)), \
         patch("app.features.screening.services.service.get_documents_by_application_id", AsyncMock(return_value=docs)), \
         patch("app.features.screening.services.service.get_active_knockout_rules", AsyncMock(return_value=[])), \
         patch("app.features.screening.services.service.get_answers_by_application_id", AsyncMock(return_value=answers)), \
         patch("app.features.screening.services.service.run_document_semantic_check", AsyncMock(return_value=doc_flags)), \
         patch("app.features.screening.services.service.get_scoring_template_by_job_id", AsyncMock(return_value=template)), \
         patch("app.features.screening.services.service.get_requirements_by_job_id", AsyncMock(return_value=[])), \
         patch("app.features.screening.services.service.match_candidate_to_job",
               AsyncMock(return_value={"match_percentage": 70.0, "matched": [], "missing": []})), \
         patch("app.features.screening.services.service.save_candidate_score", AsyncMock(side_effect=capture_save)), \
         patch("app.features.screening.services.service.add_status_log", AsyncMock()):

        from app.features.screening.services.service import process_screening
        await process_screening(1, company_id=10)

    assert len(captured_scores) == 1
    saved = captured_scores[0]
    assert saved.risk_level == "high"
    assert any("KTP" in str(f) for f in saved.red_flags)


# =============================================================================
# Test: Weighted Score Calculation
# =============================================================================

@pytest.mark.asyncio
async def test_process_screening_score_uses_custom_weights():
    """Final score harus dihitung menggunakan bobot kustom dari template."""
    app = _make_application()
    job = _make_job()
    docs = [_make_doc(DocumentType.KTP), _make_doc(DocumentType.IJAZAH)]
    answers = [
        _make_answer("skills", value_text="Python"),
        _make_answer("experience_years", value_text="0"),
    ]
    # Skill 100% weight → final = match_percentage * 100/100 = match_percentage
    template = _make_template(skill=100, exp=0, edu=0, portfolio=0, soft=0, admin=0)
    mock_db = AsyncMock()
    captured_scores = []

    async def capture_save(db, score):
        captured_scores.append(score)

    with patch("app.core.database.session.get_session", _mock_session_ctx(mock_db)), \
         patch("app.features.screening.services.service.get_application_by_id", AsyncMock(return_value=app)), \
         patch("app.features.screening.services.service.get_job_by_id", AsyncMock(return_value=job)), \
         patch("app.features.screening.services.service.get_documents_by_application_id", AsyncMock(return_value=docs)), \
         patch("app.features.screening.services.service.get_active_knockout_rules", AsyncMock(return_value=[])), \
         patch("app.features.screening.services.service.get_answers_by_application_id", AsyncMock(return_value=answers)), \
         patch("app.features.screening.services.service.run_document_semantic_check", AsyncMock(return_value=[])), \
         patch("app.features.screening.services.service.get_scoring_template_by_job_id", AsyncMock(return_value=template)), \
         patch("app.features.screening.services.service.get_requirements_by_job_id", AsyncMock(return_value=[])), \
         patch("app.features.screening.services.service.match_candidate_to_job",
               AsyncMock(return_value={"match_percentage": 60.0, "matched": [], "missing": []})), \
         patch("app.features.screening.services.service.save_candidate_score", AsyncMock(side_effect=capture_save)), \
         patch("app.features.screening.services.service.add_status_log", AsyncMock()):

        from app.features.screening.services.service import process_screening
        await process_screening(1, company_id=10)

    assert len(captured_scores) == 1
    saved = captured_scores[0]
    # final = 60.0 * 100 / 100 = 60.0
    assert abs(saved.final_score - 60.0) < 1.0, (
        f"Expected final_score ~60, got {saved.final_score}"
    )
    assert saved.skill_match_score == 60.0
