"""Knockout + Administrative Screening + AI Scoring Engine."""

from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.base import get_db
from app.core.exceptions import (
    ApplicationNotFoundException,
    MissingDocumentsException,
    RuleNotFoundException,
)
from app.features.auth.dependencies.auth import require_hr
from app.features.screening.schemas.schema import (
    KnockoutRuleCreateCommand,
    KnockoutRuleCreatedResponse,
    KnockoutRuleDeletedResponse,
    ScreeningQueuedResponse,
)
from app.features.screening.services.service import (
    create_knockout_rule as create_knockout_rule_service,
)
from app.features.screening.services.service import (
    delete_knockout_rule as delete_knockout_rule_service,
)
from app.features.screening.services.service import (
    process_screening,
    queue_screening,
)
from app.shared.schemas.response import StandardResponse

router = APIRouter(prefix="/screening", tags=["Screening Engine"])


@router.post(
    "/{job_id}/knockout-rules",
    response_model=StandardResponse[KnockoutRuleCreatedResponse],
)
async def create_knockout_rule(
    job_id: int,
    rule_name: str,
    rule_type: str,
    operator: str,
    target_value: str,
    field_key: Optional[str] = None,
    action: str = "auto_reject",
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_hr),
):
    command = KnockoutRuleCreateCommand(
        job_id=job_id,
        rule_name=rule_name,
        rule_type=rule_type,
        operator=operator,
        target_value=target_value,
        field_key=field_key,
        action=action,
    )
    result = await create_knockout_rule_service(db, command)
    return StandardResponse.ok(data=result)


@router.delete(
    "/knockout-rules/{rule_id}",
    response_model=StandardResponse[KnockoutRuleDeletedResponse],
)
async def delete_knockout_rule(
    rule_id: int, db: AsyncSession = Depends(get_db), current_user=Depends(require_hr)
):
    try:
        result = await delete_knockout_rule_service(db, rule_id)
        return StandardResponse.ok(data=result)
    except RuleNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/applications/{application_id}/run",
    response_model=StandardResponse[ScreeningQueuedResponse],
)
async def run_screening(
    application_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_hr),
):
    try:
        result = await queue_screening(
            db, current_user=current_user, application_id=application_id
        )
        background_tasks.add_task(
            process_screening_with_exception_handling,
            application_id,
            current_user.company_id,
        )
        return StandardResponse.ok(
            data=result, message="Screening started in background"
        )
    except ApplicationNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
