"""Integration tests for ranking feature with weighted scoring algorithm."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.security.jwt import create_access_token
from app.features.applications.models import (
    Application,
    ApplicationAnswer,
)
from app.features.companies.models import Company
from app.features.jobs.models import (
    Job,
    JobFormField,
    JobScoringTemplate,
)
from app.features.screening.models import CandidateScore
from app.features.users.models import User
from app.shared.enums import EmploymentType
from app.shared.enums.application_status import ApplicationStatus
from app.shared.enums.field_type import FormFieldType
from app.shared.enums.job_status import JobStatus
from app.shared.enums.user_roles import UserRole


def _make_hr_token(hr_user: User) -> str:
    """Create a valid JWT access token for HR user."""
    return create_access_token(
        data={
            "sub": str(hr_user.id),
            "role": hr_user.role.value,
            "company_id": hr_user.company_id,
            "uid": hr_user.id,
            "token_version": hr_user.token_version,
        }
    )


async def _insert_candidate_score(
    session, application_id: int, final_score: float, skill_score: float = 70.0
) -> None:
    """Helper: Insert a CandidateScore directly to avoid calling process_screening."""
    score = CandidateScore(
        application_id=application_id,
        skill_match_score=skill_score,
        experience_score=70.0,
        education_score=60.0,
        portfolio_score=50.0,
        soft_skill_score=65.0,
        administrative_score=100.0,
        final_score=final_score,
        explanation="Test explanation",
        red_flags=[],
        risk_level="low",
    )
    session.add(score)
    await session.flush()


@pytest.mark.asyncio
async def test_ranking_with_custom_weights(
    client: AsyncClient,
    test_db_session,
    override_db,
):
    """Test ranking endpoint returns results for job with custom scoring weights."""
    session = test_db_session
    unique_id = str(uuid.uuid4())[:8]

    # Setup company and HR
    company = Company(
        name=f"Ranking Company {unique_id}",
        slug=f"ranking-company-{unique_id}",
    )
    session.add(company)
    await session.flush()

    hr_user = User(
        email=f"hr_ranking_{unique_id}@test.com",
        full_name="HR Ranking Test",
        password_hash="dummy_hash",
        role=UserRole.HR,
        company_id=company.id,
        is_active=True,
    )
    session.add(hr_user)
    await session.flush()

    hr_token = _make_hr_token(hr_user)

    # Create job
    job = Job(
        title="Senior Software Engineer",
        department="Engineering",
        employment_type=EmploymentType.FULL_TIME,
        description="Test job for ranking",
        status=JobStatus.PUBLISHED,
        location="Jakarta",
        apply_code=f"RNK{unique_id}",
        company_id=company.id,
        created_by=hr_user.id,
        is_public=True,
    )
    session.add(job)
    await session.flush()

    # Custom scoring template (Skill 60%, Experience 40%)
    template = JobScoringTemplate(
        job_id=job.id,
        skill_match_weight=60,
        experience_weight=40,
        education_weight=0,
        portfolio_weight=0,
        soft_skill_weight=0,
        administrative_weight=0,
    )
    session.add(template)
    await session.flush()

    # Form fields
    ff_skill = JobFormField(
        job_id=job.id,
        field_key="skills",
        label="Skills",
        field_type=FormFieldType.TEXT,
        is_required=True,
    )
    session.add(ff_skill)
    await session.flush()

    ff_exp = JobFormField(
        job_id=job.id,
        field_key="experience_years",
        label="Years of Experience",
        field_type=FormFieldType.NUMBER,
        is_required=True,
    )
    session.add(ff_exp)
    await session.flush()

    # Create 3 candidates with different scores injected directly
    candidates_data = [
        ("Candidate A", f"cand_a_{unique_id}@test.com", "Python, FastAPI, PostgreSQL", "1", 75.0),
        ("Candidate B", f"cand_b_{unique_id}@test.com", "Basic Office", "15", 55.0),
        ("Candidate C", f"cand_c_{unique_id}@test.com", "Python, SQL, Git", "5", 85.0),
    ]
    for name, email, skills, years, score_val in candidates_data:
        cand = User(email=email, full_name=name, role=UserRole.APPLICANT)
        session.add(cand)
        await session.flush()

        application = Application(
            job_id=job.id,
            applicant_id=cand.id,
            status=ApplicationStatus.AI_PASSED,
        )
        session.add(application)
        await session.flush()

        session.add_all([
            ApplicationAnswer(
                application_id=application.id, form_field_id=ff_skill.id, value_text=skills
            ),
            ApplicationAnswer(
                application_id=application.id, form_field_id=ff_exp.id, value_text=years
            ),
        ])
        await session.flush()

        # Insert score directly — no process_screening needed
        await _insert_candidate_score(session, application.id, score_val)

    await session.commit()

    # Get ranking
    ranking_resp = await client.get(
        f"/api/v1/ranking/jobs/{job.id}",
        headers={"Authorization": f"Bearer {hr_token}"},
        params={"page": 1, "per_page": 10},
    )

    assert ranking_resp.status_code == 200
    ranking_data = ranking_resp.json()
    assert ranking_data["success"] is True

    items = ranking_data["data"]["data"]
    assert len(items) == 3
    assert all("application_id" in item for item in items)

    # Verify sorted by final_score descending: C(85) > A(75) > B(55)
    scores = [item["final_score"] for item in items]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_ranking_tenant_isolation(
    client: AsyncClient, test_db_session, override_db
):
    """Test that HR from Company A cannot see Company B's ranking."""
    session = test_db_session
    unique_id = str(uuid.uuid4())[:8]

    # Setup Company A
    company_a = Company(
        name=f"RankCoA {unique_id}",
        slug=f"rank-co-a-{unique_id}",
    )
    session.add(company_a)
    await session.flush()

    hr_a = User(
        email=f"hr_a_rank_{unique_id}@test.com",
        full_name="HR A Rank",
        password_hash="dummy_hash",
        role=UserRole.HR,
        company_id=company_a.id,
        is_active=True,
    )
    session.add(hr_a)
    await session.flush()

    # Setup Company B
    company_b = Company(
        name=f"RankCoB {unique_id}",
        slug=f"rank-co-b-{unique_id}",
    )
    session.add(company_b)
    await session.flush()

    hr_b = User(
        email=f"hr_b_rank_{unique_id}@test.com",
        full_name="HR B Rank",
        password_hash="dummy_hash",
        role=UserRole.HR,
        company_id=company_b.id,
        is_active=True,
    )
    session.add(hr_b)
    await session.flush()

    # Create job for Company B
    job_b = Job(
        title="Company B Job",
        employment_type=EmploymentType.FULL_TIME,
        description="Company B job for ranking",
        status=JobStatus.PUBLISHED,
        location="Jakarta",
        apply_code=f"RANKCOB{unique_id}",
        company_id=company_b.id,
        created_by=hr_b.id,
        is_public=True,
    )
    session.add(job_b)
    await session.flush()
    job_b_id = job_b.id

    await session.commit()

    # HR from Company A tries to access Company B's ranking — should be 404
    hr_a_token = _make_hr_token(hr_a)

    ranking_resp = await client.get(
        f"/api/v1/ranking/jobs/{job_b_id}",
        headers={"Authorization": f"Bearer {hr_a_token}"},
    )

    assert ranking_resp.status_code == 404


@pytest.mark.asyncio
async def test_ranking_top_n_limit(
    client: AsyncClient,
    test_db_session,
    override_db,
):
    """Test ranking with top_n limit returns at most N results."""
    session = test_db_session
    unique_id = str(uuid.uuid4())[:8]

    company = Company(
        name=f"TopNRanking {unique_id}",
        slug=f"topn-ranking-{unique_id}",
    )
    session.add(company)
    await session.flush()

    hr_user = User(
        email=f"hr_topn_{unique_id}@test.com",
        full_name="HR TopN Ranking",
        password_hash="dummy_hash",
        role=UserRole.HR,
        company_id=company.id,
        is_active=True,
    )
    session.add(hr_user)
    await session.flush()

    hr_token = _make_hr_token(hr_user)

    job = Job(
        title="TopN Test Job",
        employment_type=EmploymentType.FULL_TIME,
        description="Test job for top N",
        status=JobStatus.PUBLISHED,
        location="Jakarta",
        apply_code=f"TOPN{unique_id}",
        company_id=company.id,
        created_by=hr_user.id,
        is_public=True,
    )
    session.add(job)
    await session.flush()

    ff = JobFormField(
        job_id=job.id,
        field_key="skills",
        label="Skills",
        field_type=FormFieldType.TEXT,
        is_required=True,
    )
    session.add(ff)
    await session.flush()

    # Create 3 candidates with scores
    scores_vals = [80.0, 65.0, 90.0]
    for i in range(3):
        cand = User(
            email=f"topn_cand_{i}_{unique_id}@test.com",
            full_name=f"TopN Candidate {i}",
            role=UserRole.APPLICANT,
        )
        session.add(cand)
        await session.flush()

        application = Application(
            job_id=job.id,
            applicant_id=cand.id,
            status=ApplicationStatus.AI_PASSED,
        )
        session.add(application)
        await session.flush()

        session.add(ApplicationAnswer(
            application_id=application.id,
            form_field_id=ff.id,
            value_text=f"Skill {i}",
        ))
        await session.flush()

        await _insert_candidate_score(session, application.id, scores_vals[i])

    await session.commit()

    # Get ranking with top_n=2
    ranking_resp = await client.get(
        f"/api/v1/ranking/jobs/{job.id}",
        headers={"Authorization": f"Bearer {hr_token}"},
        params={"page": 1, "per_page": 10, "top_n": 2},
    )

    assert ranking_resp.status_code == 200
    ranking_data = ranking_resp.json()
    assert ranking_data["success"] is True

    items = ranking_data["data"]["data"]
    assert len(items) <= 2


@pytest.mark.asyncio
async def test_ranking_pagination(
    client: AsyncClient,
    test_db_session,
    override_db,
):
    """Test ranking pagination returns correct page structure."""
    session = test_db_session
    unique_id = str(uuid.uuid4())[:8]

    company = Company(
        name=f"PagRanking {unique_id}",
        slug=f"pag-ranking-{unique_id}",
    )
    session.add(company)
    await session.flush()

    hr_user = User(
        email=f"hr_pag_{unique_id}@test.com",
        full_name="HR Pag Ranking",
        password_hash="dummy_hash",
        role=UserRole.HR,
        company_id=company.id,
        is_active=True,
    )
    session.add(hr_user)
    await session.flush()

    hr_token = _make_hr_token(hr_user)

    job = Job(
        title="Pagination Test Job",
        employment_type=EmploymentType.FULL_TIME,
        description="Test job for pagination",
        status=JobStatus.PUBLISHED,
        location="Jakarta",
        apply_code=f"PAG{unique_id}",
        company_id=company.id,
        created_by=hr_user.id,
        is_public=True,
    )
    session.add(job)
    await session.flush()

    ff = JobFormField(
        job_id=job.id,
        field_key="skills",
        label="Skills",
        field_type=FormFieldType.TEXT,
        is_required=True,
    )
    session.add(ff)
    await session.flush()

    # Create 5 candidates with distinct scores
    score_vals = [90.0, 80.0, 70.0, 60.0, 50.0]
    for i in range(5):
        cand = User(
            email=f"pag_cand_{i}_{unique_id}@test.com",
            full_name=f"Pag Candidate {i}",
            role=UserRole.APPLICANT,
        )
        session.add(cand)
        await session.flush()

        application = Application(
            job_id=job.id,
            applicant_id=cand.id,
            status=ApplicationStatus.AI_PASSED,
        )
        session.add(application)
        await session.flush()

        session.add(ApplicationAnswer(
            application_id=application.id,
            form_field_id=ff.id,
            value_text=f"Skill {i}",
        ))
        await session.flush()

        await _insert_candidate_score(session, application.id, score_vals[i])

    await session.commit()

    # Page 1 — 2 per page
    ranking_resp_1 = await client.get(
        f"/api/v1/ranking/jobs/{job.id}",
        headers={"Authorization": f"Bearer {hr_token}"},
        params={"page": 1, "per_page": 2},
    )

    assert ranking_resp_1.status_code == 200
    data_1 = ranking_resp_1.json()
    assert data_1["success"] is True
    assert len(data_1["data"]["data"]) == 2
    assert data_1["data"]["total"] == 5
    assert data_1["data"]["has_next"] is True
    assert data_1["data"]["has_prev"] is False

    # Page 2
    ranking_resp_2 = await client.get(
        f"/api/v1/ranking/jobs/{job.id}",
        headers={"Authorization": f"Bearer {hr_token}"},
        params={"page": 2, "per_page": 2},
    )

    assert ranking_resp_2.status_code == 200
    data_2 = ranking_resp_2.json()
    assert len(data_2["data"]["data"]) == 2
    assert data_2["data"]["has_prev"] is True
    assert data_2["data"]["has_next"] is True

    # Page 3 — 1 remaining
    ranking_resp_3 = await client.get(
        f"/api/v1/ranking/jobs/{job.id}",
        headers={"Authorization": f"Bearer {hr_token}"},
        params={"page": 3, "per_page": 2},
    )

    assert ranking_resp_3.status_code == 200
    data_3 = ranking_resp_3.json()
    assert len(data_3["data"]["data"]) == 1
    assert data_3["data"]["has_next"] is False
