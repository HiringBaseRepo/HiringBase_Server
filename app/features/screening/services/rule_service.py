"""Knockout rule service."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import RuleNotFoundException
from app.features.jobs.models import JobKnockoutRule
from app.features.screening.repositories.repository import (
    get_knockout_rule_by_id,
    save_knockout_rule,
)
from app.features.screening.repositories.repository import (
    delete_knockout_rule as delete_knockout_rule_query,
)
from app.features.screening.schemas.schema import (
    KnockoutRuleCreateCommand,
    KnockoutRuleCreatedResponse,
    KnockoutRuleDeletedResponse,
)
from app.features.screening.services.helpers import normalize_knockout_operator


async def create_knockout_rule(
    db: AsyncSession,
    data: KnockoutRuleCreateCommand,
) -> KnockoutRuleCreatedResponse:
    rule = JobKnockoutRule(
        job_id=data.job_id,
        rule_name=data.rule_name,
        rule_type=data.rule_type.value,
        field_key=data.field_key,
        operator=normalize_knockout_operator(data.operator.value),
        target_value=data.target_value,
        action=data.action.value,
    )
    rule = await save_knockout_rule(db, rule)
    await db.commit()
    return KnockoutRuleCreatedResponse(rule_id=rule.id, job_id=data.job_id)


async def delete_knockout_rule(
    db: AsyncSession, rule_id: int
) -> KnockoutRuleDeletedResponse:
    rule = await get_knockout_rule_by_id(db, rule_id)
    if not rule:
        raise RuleNotFoundException()
    await delete_knockout_rule_query(db, rule)
    await db.commit()
    return KnockoutRuleDeletedResponse(deleted=True)
