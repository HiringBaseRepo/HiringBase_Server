"""Screening data access helpers."""
from datetime import datetime

from sqlalchemy import and_, case, or_, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.applications.models import (
    Application,
    ApplicationAnswer,
    ApplicationDocument,
    ApplicationStatusLog,
)
from app.features.audit_logs.models import AuditLog
from app.features.screening.models import CandidateScore
from app.features.jobs.models import (
    Job,
    JobKnockoutRule,
    JobRequirement,
    JobScoringTemplate,
)


async def get_application_for_company(
    db: AsyncSession,
    *,
    application_id: int,
    company_id: int | None,
) -> Application | None:
    result = await db.execute(
        select(Application)
        .options(selectinload(Application.applicant))
        .join(Job).where(
            Application.id == application_id,
            Job.company_id == company_id,
        )
    )
    return result.scalar_one_or_none()


async def get_application_by_id(db: AsyncSession, application_id: int) -> Application | None:
    result = await db.execute(
        select(Application)
        .options(selectinload(Application.applicant))
        .where(Application.id == application_id)
    )
    return result.scalar_one_or_none()


async def get_job_by_id(db: AsyncSession, job_id: int) -> Job | None:
    result = await db.execute(select(Job).where(Job.id == job_id))
    return result.scalar_one_or_none()


async def save_knockout_rule(db: AsyncSession, rule: JobKnockoutRule) -> JobKnockoutRule:
    db.add(rule)
    await db.flush()
    await db.refresh(rule)
    return rule


async def get_knockout_rule_by_id(db: AsyncSession, rule_id: int) -> JobKnockoutRule | None:
    result = await db.execute(select(JobKnockoutRule).where(JobKnockoutRule.id == rule_id))
    return result.scalar_one_or_none()


async def delete_knockout_rule(db: AsyncSession, rule: JobKnockoutRule) -> None:
    await db.delete(rule)
    await db.flush()


async def get_documents_by_application_id(db: AsyncSession, application_id: int) -> list[ApplicationDocument]:
    result = await db.execute(select(ApplicationDocument).where(ApplicationDocument.application_id == application_id))
    return list(result.scalars().all())


async def get_active_knockout_rules(db: AsyncSession, job_id: int) -> list[JobKnockoutRule]:
    result = await db.execute(
        select(JobKnockoutRule).where(JobKnockoutRule.job_id == job_id, JobKnockoutRule.is_active)
    )
    return list(result.scalars().all())


async def get_answers_by_application_id(db: AsyncSession, application_id: int) -> list[ApplicationAnswer]:
    result = await db.execute(
        select(ApplicationAnswer)
        .options(selectinload(ApplicationAnswer.form_field))
        .where(ApplicationAnswer.application_id == application_id)
    )
    return list(result.scalars().all())


async def get_scoring_template_by_job_id(db: AsyncSession, job_id: int) -> JobScoringTemplate | None:
    result = await db.execute(select(JobScoringTemplate).where(JobScoringTemplate.job_id == job_id))
    return result.scalar_one_or_none()


async def get_candidate_score_by_app_id(db: AsyncSession, application_id: int) -> CandidateScore | None:
    result = await db.execute(select(CandidateScore).where(CandidateScore.application_id == application_id))
    return result.scalar_one_or_none()


async def get_requirements_by_job_id(db: AsyncSession, job_id: int) -> list[JobRequirement]:
    result = await db.execute(select(JobRequirement).where(JobRequirement.job_id == job_id))
    return list(result.scalars().all())


async def save_candidate_score(db: AsyncSession, score: CandidateScore) -> CandidateScore:
    db.add(score)
    await db.flush()
    return score


async def add_status_log(db: AsyncSession, log: ApplicationStatusLog) -> None:
    db.add(log)


async def get_candidate_score_for_company(
    db: AsyncSession,
    *,
    application_id: int,
    company_id: int | None,
) -> CandidateScore | None:
    result = await db.execute(
        select(CandidateScore).join(Application).join(Job).where(
            Application.id == application_id,
            Job.company_id == company_id,
        )
    )
    return result.scalar_one_or_none()


async def add_audit_log(db: AsyncSession, audit: AuditLog) -> None:
    db.add(audit)


async def get_pending_applications_for_batch(db: AsyncSession) -> list[tuple[int, int]]:
    """Get all applications with status APPLIED for batch processing."""
    from app.shared.enums.application_status import ApplicationStatus
    
    stmt = select(Application.id, Job.company_id).join(Job).where(
        Application.status == ApplicationStatus.APPLIED
    )
    result = await db.execute(stmt)
    return list(result.all())


async def get_batch_screening_candidates(
    db: AsyncSession,
    *,
    stale_before: datetime,
    limit: int,
) -> list[tuple[int, int | None, str]]:
    """Get ordered candidates for hourly batch screening."""
    from app.shared.enums.application_status import ApplicationStatus

    priority = case(
        (
            Application.status.in_(
                [ApplicationStatus.DOC_CHECK, ApplicationStatus.AI_PROCESSING]
            ),
            0,
        ),
        else_=1,
    )
    stmt = (
        select(Application.id, Job.company_id, Application.status)
        .join(Job)
        .where(
            or_(
                Application.status == ApplicationStatus.APPLIED,
                and_(
                    Application.status.in_(
                        [ApplicationStatus.DOC_CHECK, ApplicationStatus.AI_PROCESSING]
                    ),
                    Application.updated_at <= stale_before,
                ),
            )
        )
        .order_by(priority.asc(), Application.updated_at.asc(), Application.id.asc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = []
    for application_id, company_id, status in result.all():
        rows.append((application_id, company_id, status.value))
    return rows
