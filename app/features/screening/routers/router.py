"""Knockout + Administrative Screening + AI Scoring Engine."""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.base import get_db
from app.features.auth.dependencies.auth import HrUserDep
from app.features.screening.schemas.schema import (
    KnockoutRuleCreateCommand,
    KnockoutRuleCreatedResponse,
    KnockoutRuleDeletedResponse,
    ScreeningQueuedResponse,
)
from app.features.screening.services.service import (
    create_knockout_rule as create_knockout_rule_service,
    delete_knockout_rule as delete_knockout_rule_service,
    queue_screening,
)
from app.features.screening.tasks import run_screening_task
from app.shared.schemas.response import StandardResponse
from app.shared.helpers.localization import get_label

router = APIRouter(prefix="/screening", tags=["Screening Engine"])
DbDep = Annotated[AsyncSession, Depends(get_db)]


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
    db: DbDep,
    current_user: HrUserDep,
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
    rule_id: int, db: DbDep, current_user: HrUserDep
):
    result = await delete_knockout_rule_service(db, rule_id)
    return StandardResponse.ok(data=result)


@router.post(
    "/applications/{application_id}/run",
    response_model=StandardResponse[ScreeningQueuedResponse],
)
async def run_screening(
    application_id: int,
    db: DbDep,
    current_user: HrUserDep,
):
    result = await queue_screening(
        db, current_user=current_user, application_id=application_id
    )
    # Panggil task eksternal via Taskiq
    await run_screening_task.kiq(
        application_id=application_id,
        company_id=current_user.company_id,
    )
    return StandardResponse.ok(
        data=result, message=get_label("Screening started in background")
    )
