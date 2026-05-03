"""HR Manual Override API."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.base import get_db
from app.features.auth.dependencies.auth import require_hr
from app.features.screening.schemas.schema import ManualOverrideResponse
from app.features.screening.services.service import manual_override_score as manual_override_score_service
from app.shared.schemas.response import StandardResponse

router = APIRouter(prefix="/manual-override", tags=["Manual Override"])


@router.post("/{application_id}", response_model=StandardResponse[ManualOverrideResponse])
async def manual_override_score(
    application_id: int,
    skill_adjustment: float = 0.0,
    experience_adjustment: float = 0.0,
    education_adjustment: float = 0.0,
    portfolio_adjustment: float = 0.0,
    soft_skill_adjustment: float = 0.0,
    admin_adjustment: float = 0.0,
    reason: str = "",
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_hr),
):
    result = await manual_override_score_service(
        db,
        current_user=current_user,
        application_id=application_id,
        skill_adjustment=skill_adjustment,
        experience_adjustment=experience_adjustment,
        education_adjustment=education_adjustment,
        portfolio_adjustment=portfolio_adjustment,
        soft_skill_adjustment=soft_skill_adjustment,
        admin_adjustment=admin_adjustment,
        reason=reason,
    )
    return StandardResponse.ok(data=result)
