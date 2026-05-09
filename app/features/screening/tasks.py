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

@broker.task(schedule=[{"cron": "0 * * * *"}])
async def run_batch_screening() -> None:
    """
    Task periodik (setiap jam) untuk memproses semua aplikasi yang masih berstatus APPLIED.
    """
    from app.core.database.session import get_session
    from sqlalchemy import select
    from app.features.applications.models import Application
    from app.features.jobs.models import Job
    from app.shared.enums.application_status import ApplicationStatus

    logger.info("Starting batch screening task")
    
    async with get_session() as db:
        # Cari semua aplikasi dengan status APPLIED
        stmt = select(Application.id, Job.company_id).join(Job).where(
            Application.status == ApplicationStatus.APPLIED
        )
        result = await db.execute(stmt)
        pending_apps = result.all()
        
        if not pending_apps:
            logger.info("No pending applications for batch screening")
            return

        logger.info(f"Enqueuing {len(pending_apps)} applications for screening")
        
        for app_id, company_id in pending_apps:
            await run_screening_task.kiq(
                application_id=app_id,
                company_id=company_id
            )

    logger.info("Batch screening task enqueued all pending applications")
