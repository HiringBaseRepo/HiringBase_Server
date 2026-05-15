"""Screening Background Tasks."""
from typing import Annotated
import asyncio
from datetime import timedelta, timezone, datetime
from sqlalchemy.exc import DBAPIError
from taskiq import TaskiqDepends, Context
from app.core.tkq import broker
from app.core.config import settings
from app.features.screening.repositories.repository import get_batch_screening_candidates
from app.features.screening.services.quota import (
    acquire_processing_quota,
    clear_screening_queued,
    get_recovery_retry_count,
    increment_recovery_retry_count,
    is_screening_queued_or_processing,
    mark_screening_queued,
    release_processing_quota,
)
from app.features.screening.services.service import (
    handle_screening_failure,
    process_screening_with_exception_handling,
)
import structlog

logger = structlog.get_logger(__name__)

_BATCH_QUERY_MAX_ATTEMPTS = 3
_BATCH_QUERY_RETRY_DELAY_SECONDS = 1


def _is_transient_db_disconnect(exc: DBAPIError) -> bool:
    if exc.connection_invalidated:
        return True

    detail = str(exc.orig).lower() if exc.orig else str(exc).lower()
    transient_markers = (
        "connection was closed in the middle of operation",
        "connectiondoesnotexisterror",
        "server closed the connection unexpectedly",
        "connection is closed",
    )
    return any(marker in detail for marker in transient_markers)


async def _load_batch_screening_candidates_with_retry(
    *,
    stale_before: datetime,
    limit: int,
) -> list[tuple[int, int | None, str]]:
    from app.core.database.session import get_session

    last_exc: DBAPIError | None = None

    for attempt in range(1, _BATCH_QUERY_MAX_ATTEMPTS + 1):
        try:
            async with get_session() as db:
                return await get_batch_screening_candidates(
                    db,
                    stale_before=stale_before,
                    limit=limit,
                )
        except DBAPIError as exc:
            if not _is_transient_db_disconnect(exc) or attempt == _BATCH_QUERY_MAX_ATTEMPTS:
                raise

            last_exc = exc
            logger.warning(
                "batch_screening_candidate_query_retry",
                attempt=attempt,
                max_attempts=_BATCH_QUERY_MAX_ATTEMPTS,
                error=str(exc),
            )
            await asyncio.sleep(_BATCH_QUERY_RETRY_DELAY_SECONDS)

    if last_exc:
        raise last_exc
    return []

@broker.task(retry_on_error=True, max_retries=3)
async def run_screening_task(
    application_id: int, 
    company_id: int,
    trigger_source: str = "manual",
    is_recovery: bool = False,
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
        attempt=retry_count + 1,
        trigger_source=trigger_source,
    )
    
    # Jika sudah mencapai retry terakhir (misal max_retries=3, berarti attempt ke-4),
    # kita bisa instruksikan service untuk menggunakan fallback jika gagal lagi.
    use_fallback_on_error = retry_count >= 3

    quota = await acquire_processing_quota(
        application_id,
        trigger_source=trigger_source,
    )
    if not quota.allowed:
        logger.info(
            "Background screening task deferred by quota guard",
            application_id=application_id,
            company_id=company_id,
            trigger_source=trigger_source,
            reason=quota.reason,
        )
        return

    try:
        if is_recovery:
            await increment_recovery_retry_count(application_id)

        processed_successfully = await process_screening_with_exception_handling(
            application_id=application_id, 
            company_id=company_id,
            trigger_source=trigger_source,
            force_fallback=use_fallback_on_error
        )
        if processed_successfully:
            logger.info(
                "Background screening task completed",
                application_id=application_id,
                trigger_source=trigger_source,
            )
        else:
            logger.warning(
                "Background screening task moved to manual review fallback",
                application_id=application_id,
                trigger_source=trigger_source,
            )
    except Exception as e:
        logger.error(
            "Background screening task failed", 
            application_id=application_id, 
            error=str(e),
            attempt=retry_count + 1,
            trigger_source=trigger_source,
        )
        raise
    finally:
        await release_processing_quota(
            application_id,
            trigger_source=trigger_source,
        )
        await clear_screening_queued(application_id)

@broker.task(schedule=[{"cron": "0 * * * *"}])
async def run_batch_screening() -> None:
    """
    Task periodik (setiap jam) untuk memproses semua aplikasi yang masih berstatus APPLIED.
    """
    from app.shared.enums.application_status import ApplicationStatus

    logger.info("Starting batch screening task")

    stale_before = datetime.now(timezone.utc) - timedelta(
        hours=settings.SCREENING_STALE_TIMEOUT_HOURS
    )
    candidates = await _load_batch_screening_candidates_with_retry(
        stale_before=stale_before,
        limit=settings.SCREENING_BATCH_MAX_PER_RUN,
    )

    if not candidates:
        logger.info("No pending applications for batch screening")
        return

    scanned = len(candidates)
    queued = 0
    skipped_duplicate = 0
    skipped_recovery_limit = 0

    for app_id, company_id, status in candidates:
        if await is_screening_queued_or_processing(app_id):
            skipped_duplicate += 1
            continue

        if status in {
            ApplicationStatus.DOC_CHECK.value,
            ApplicationStatus.AI_PROCESSING.value,
        }:
            retry_count = await get_recovery_retry_count(app_id)
            if retry_count >= settings.SCREENING_RECOVERY_RETRY_LIMIT:
                skipped_recovery_limit += 1
                await handle_screening_failure(
                    application_id=app_id,
                    company_id=company_id,
                    trigger_source="batch",
                    reason="stale_screening_retry_limit_reached",
                )
                await clear_screening_queued(app_id)
                continue
        marked = await mark_screening_queued(app_id)
        if not marked:
            skipped_duplicate += 1
            continue

        await run_screening_task.kiq(
            application_id=app_id,
            company_id=company_id,
            trigger_source="batch",
            is_recovery=status
            in {
                ApplicationStatus.DOC_CHECK.value,
                ApplicationStatus.AI_PROCESSING.value,
            },
        )
        queued += 1
        await asyncio.sleep(settings.SCREENING_BATCH_ENQUEUE_DELAY_SECONDS)

    logger.info(
        "Batch screening task finished",
        scanned=scanned,
        queued=queued,
        skipped_duplicate=skipped_duplicate,
        skipped_recovery_limit=skipped_recovery_limit,
    )
