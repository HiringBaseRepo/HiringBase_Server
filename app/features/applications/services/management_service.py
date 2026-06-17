"""Management application service for internal HR actions."""

import json
import structlog

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.audit_logs.models import AuditLog
from app.features.audit_logs.repositories.repository import create_audit_log
from app.core.exceptions import ApplicationNotFoundException
from app.core.utils.pagination import PaginationParams
from app.features.applications.models import ApplicationStatusLog
from app.features.applications.repositories.repository import (
    add_status_log,
    get_application_for_company,
    list_applications as list_applications_query,
    update_application_status as update_application_status_repo,
    get_application_detail as get_application_detail_repo,
)
from app.features.applications.schemas.schema import (
    ApplicationListItem,
    ApplicationStatusUpdateResponse,
    ApplicationDetailResponse,
    ApplicationAnswerResponse,
    ApplicationDocumentResponse,
    CandidateScoreResponse,
)
from app.shared.helpers.localization import get_label
from app.features.notifications.services.service import create_notification_for_internal_audience
from app.features.users.models import User
from app.shared.constants.audit_actions import APPLICATION_STATUS_UPDATE
from app.shared.constants.audit_entities import APPLICATION
from app.shared.enums.application_status import ApplicationStatus
from app.shared.enums.notification_type import NotificationType
from app.shared.schemas.response import PaginatedResponse

logger = structlog.get_logger(__name__)


async def list_applications(
    db: AsyncSession,
    *,
    current_user: User,
    pagination: PaginationParams,
    job_id: int | None = None,
    status_filter: ApplicationStatus | None = None,
    q: str | None = None,
) -> PaginatedResponse[ApplicationListItem]:
    applications, total = await list_applications_query(
        db,
        company_id=current_user.company_id,
        pagination=pagination,
        job_id=job_id,
        status=status_filter,
        q=q,
    )
    pages = (total + pagination.per_page - 1) // pagination.per_page
    
    items = []
    for app in applications:
        item_data = {
            "id": app.id,
            "job_id": app.job_id,
            "applicant_id": app.applicant_id,
            "status": app.status.value,
            "status_label": get_label(app.status),
            "created_at": app.created_at.isoformat() if app.created_at else None,
            "applicant_name": app.applicant.full_name if app.applicant else None,
        }
        items.append(ApplicationListItem.model_validate(item_data))

    return PaginatedResponse(
        data=items,
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
        total_pages=pages,
        has_next=pagination.page < pages,
        has_prev=pagination.page > 1,
    )


async def update_application_status(
    db: AsyncSession,
    *,
    current_user: User,
    application_id: int,
    new_status: ApplicationStatus,
    reason: str | None = None,
) -> ApplicationStatusUpdateResponse:
    application = await get_application_for_company(
        db,
        application_id=application_id,
        company_id=current_user.company_id,
    )
    if not application:
        raise ApplicationNotFoundException()
    from app.core.utils.audit import get_model_snapshot
    old_values = get_model_snapshot(application)
    old_status = application.status
    
    await update_application_status_repo(db, application, new_status)
    await add_status_log(
        db,
        ApplicationStatusLog(
            application_id=application.id,
            from_status=old_status.value if old_status else None,
            to_status=new_status.value,
            changed_by=current_user.id,
            reason=reason,
        ),
    )
    await create_audit_log(
        db,
        AuditLog(
            company_id=current_user.company_id,
            user_id=current_user.id,
            action=APPLICATION_STATUS_UPDATE,
            entity_type=APPLICATION,
            entity_id=application.id,
            old_values=old_values,
            new_values={"status": new_status.value, "reason": reason},
        ),
    )
    status_notification_type = {
        ApplicationStatus.OFFERED: NotificationType.APPLICATION_OFFERED,
        ApplicationStatus.HIRED: NotificationType.APPLICATION_HIRED,
        ApplicationStatus.REJECTED: NotificationType.APPLICATION_REJECTED,
    }.get(new_status)
    if status_notification_type:
        await create_notification_for_internal_audience(
            db,
            actor_user_id=current_user.id,
            company_id=current_user.company_id,
            notification_type=status_notification_type,
            entity_type=APPLICATION,
            entity_id=application.id,
            message_params={
                "applicant_name": application.applicant.full_name if application.applicant else "-",
                "job_title": application.job.title if application.job else "-",
            },
        )
    await db.commit()
    return ApplicationStatusUpdateResponse(
        application_id=application.id,
        old_status=old_status.value if old_status else None,
        new_status=new_status.value,
        new_status_label=get_label(new_status),
    )


async def get_application_detail(
    db: AsyncSession,
    *,
    current_user: User,
    application_id: int,
) -> ApplicationDetailResponse:
    application = await get_application_detail_repo(
        db, application_id=application_id, company_id=current_user.company_id
    )
    if not application:
        raise ApplicationNotFoundException()

    logger.debug(
        "application_detail_loaded",
        application_id=application.id,
        answers_count=len(application.answers),
        documents_count=len(application.documents),
    )
    
    answers = []
    for ans in application.answers:
        answers.append(
            ApplicationAnswerResponse(
                field_key=ans.form_field.field_key if ans.form_field else "unknown",
                label=ans.form_field.label if ans.form_field else "Unknown Field",
                value=ans.value_text or ans.value_number or ans.value_json,
            )
        )
    
    # Fallback to notes if no formal answers found
    if not answers and application.notes:
        try:
            notes_data = json.loads(application.notes)
            for key, value in notes_data.items():
                answers.append(
                    ApplicationAnswerResponse(
                        field_key=key,
                        label=key.replace("_", " ").title(),
                        value=value,
                    )
                )
            logger.debug(
                "application_notes_fallback_used",
                application_id=application.id,
                answers_count=len(answers),
            )
        except (json.JSONDecodeError, TypeError) as exc:
            logger.warning(
                "application_notes_fallback_parse_failed",
                application_id=application.id,
                error=str(exc),
            )

    documents = []
    for doc in application.documents:
        documents.append(
            ApplicationDocumentResponse(
                id=doc.id,
                document_type=doc.document_type.value,
                file_name=doc.file_name,
                file_url=doc.file_url,
            )
        )

    score = None
    if application.scores:
        s = application.scores[0] if isinstance(application.scores, list) else application.scores
        score = CandidateScoreResponse(
            skill_match_score=s.skill_match_score,
            experience_score=s.experience_score,
            education_score=s.education_score,
            portfolio_score=s.portfolio_score,
            soft_skill_score=s.soft_skill_score,
            administrative_score=s.administrative_score,
            final_score=s.final_score,
            explanation=s.explanation,
            red_flags=s.red_flags,
            risk_level=s.risk_level,
            scoring_breakdown=s.scoring_breakdown,
        )

    rejection_reason = None
    if application.status_logs:
        rejected_logs = [log for log in application.status_logs if log.to_status == "rejected"]
        if rejected_logs:
            # Sort by created_at desc or use last if created_at is not null
            rejected_logs.sort(key=lambda x: x.created_at or datetime.min, reverse=True)
            rejection_reason = rejected_logs[0].reason

    return ApplicationDetailResponse(
        id=application.id,
        job_id=application.job_id,
        job_title=application.job.title,
        applicant_name=application.applicant.full_name,
        applicant_email=application.applicant.email,
        status=application.status.value,
        status_label=get_label(application.status),
        created_at=application.created_at,
        answers=answers,
        documents=documents,
        score=score,
        rejection_reason=rejection_reason,
    )
