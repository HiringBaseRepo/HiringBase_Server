"""Screening Background Tasks."""
from typing import Annotated
from taskiq import TaskiqDepends, Context
from app.core.tkq import broker
from app.features.screening.services.service import process_screening_with_exception_handling
import structlog

logger = structlog.get_logger(__name__)

@broker.task(retry_on_error=True, max_retries=3)
async def run_screening_task(
    application_id: int, 
    company_id: int,
    context: Annotated[Context, TaskiqDepends()] = None,
) -> None:
    """
    Taskiq worker untuk menjalankan proses screening di background dengan retry.
    """
    retry_count = 0
    if context and context.message.labels:
        retry_count = int(context.message.labels.get("retry_count", 0))

    logger.info(
        "Starting background screening task", 
        application_id=application_id, 
        company_id=company_id,
        attempt=retry_count + 1
    )
    
    # Jika sudah mencapai retry terakhir (misal max_retries=3, berarti attempt ke-4),
    # kita bisa instruksikan service untuk menggunakan fallback jika gagal lagi.
    use_fallback_on_error = retry_count >= 3

    try:
        await process_screening_with_exception_handling(
            application_id=application_id, 
            company_id=company_id,
            force_fallback=use_fallback_on_error
        )
        logger.info("Background screening task completed", application_id=application_id)
    except Exception as e:
        logger.error(
            "Background screening task failed", 
            application_id=application_id, 
            error=str(e),
            attempt=retry_count + 1
        )
        raise
