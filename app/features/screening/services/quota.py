"""Redis-backed quota and idempotency helpers for screening."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.core.cache.client import redis_client
from app.core.config import settings


@dataclass(slots=True)
class ScreeningEnqueueDecision:
    queue_status: str
    task_enqueued: bool
    reason: str | None = None


@dataclass(slots=True)
class ProcessingQuotaDecision:
    allowed: bool
    reason: str | None = None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _queue_marker_key(application_id: int) -> str:
    return f"screening:queued:{application_id}"


def _processing_lock_key(application_id: int) -> str:
    return f"screening:processing:{application_id}"


def _hourly_counter_key(now: datetime) -> str:
    return now.strftime("screening:quota:hour:%Y%m%d%H")


def _daily_counter_key(now: datetime) -> str:
    return now.strftime("screening:quota:day:%Y%m%d")


def _parallel_counter_key(source: str) -> str:
    return f"screening:parallel:{source}"


def _recovery_retry_key(application_id: int) -> str:
    return f"screening:recovery:{application_id}"


def _guard_lock_key() -> str:
    return "screening:guard:lock"


async def _get_int(key: str) -> int:
    redis = redis_client.redis
    if not redis:
        return 0
    value = await redis.get(key)
    try:
        return int(value) if value is not None else 0
    except (TypeError, ValueError):
        return 0


async def register_manual_screening_request(application_id: int) -> ScreeningEnqueueDecision:
    """Prepare manual screening request without overscheduling work."""
    if await is_screening_queued_or_processing(application_id):
        return ScreeningEnqueueDecision(
            queue_status="duplicate",
            task_enqueued=False,
            reason="screening_already_queued",
        )

    if not await has_manual_capacity():
        return ScreeningEnqueueDecision(
            queue_status="pending_quota",
            task_enqueued=False,
            reason="screening_pending_quota",
        )

    marked = await mark_screening_queued(application_id)
    if not marked:
        return ScreeningEnqueueDecision(
            queue_status="duplicate",
            task_enqueued=False,
            reason="screening_already_queued",
        )

    return ScreeningEnqueueDecision(queue_status="queued", task_enqueued=True)


async def has_manual_capacity() -> bool:
    """Cheap capacity check to avoid manual enqueue spam."""
    redis = redis_client.redis
    if not redis:
        return True

    now = _utc_now()
    total_parallel = await _get_int(_parallel_counter_key("total"))
    manual_parallel = await _get_int(_parallel_counter_key("manual"))
    hourly = await _get_int(_hourly_counter_key(now))
    daily = await _get_int(_daily_counter_key(now))

    return (
        total_parallel < settings.SCREENING_MAX_PARALLEL_TOTAL
        and manual_parallel < settings.SCREENING_MANUAL_MAX_PARALLEL
        and hourly < settings.SCREENING_MAX_PER_HOUR
        and daily < settings.SCREENING_MAX_PER_DAY
    )


async def is_screening_queued_or_processing(application_id: int) -> bool:
    redis = redis_client.redis
    if not redis:
        return False
    return bool(
        await redis.exists(
            _queue_marker_key(application_id),
            _processing_lock_key(application_id),
        )
    )


async def mark_screening_queued(application_id: int) -> bool:
    redis = redis_client.redis
    if not redis:
        return True
    return bool(
        await redis.set(
            _queue_marker_key(application_id),
            "1",
            ex=settings.SCREENING_ENQUEUE_COOLDOWN_SECONDS,
            nx=True,
        )
    )


async def clear_screening_queued(application_id: int) -> None:
    redis = redis_client.redis
    if not redis:
        return
    await redis.delete(_queue_marker_key(application_id))


async def acquire_processing_quota(
    application_id: int,
    *,
    trigger_source: str,
) -> ProcessingQuotaDecision:
    """Acquire processing lock and quota counters with low-concurrency guard."""
    redis = redis_client.redis
    if not redis:
        return ProcessingQuotaDecision(allowed=True)

    guard_lock = await redis.set(_guard_lock_key(), "1", ex=10, nx=True)
    if not guard_lock:
        return ProcessingQuotaDecision(allowed=False, reason="guard_busy")

    now = _utc_now()
    processing_key = _processing_lock_key(application_id)
    source_counter_key = _parallel_counter_key(trigger_source)
    total_counter_key = _parallel_counter_key("total")
    hourly_key = _hourly_counter_key(now)
    daily_key = _daily_counter_key(now)

    try:
        if await redis.exists(processing_key):
            return ProcessingQuotaDecision(allowed=False, reason="already_processing")

        total_parallel = await _get_int(total_counter_key)
        if total_parallel >= settings.SCREENING_MAX_PARALLEL_TOTAL:
            return ProcessingQuotaDecision(allowed=False, reason="max_parallel_total")

        if trigger_source == "manual":
            manual_parallel = await _get_int(source_counter_key)
            if manual_parallel >= settings.SCREENING_MANUAL_MAX_PARALLEL:
                return ProcessingQuotaDecision(allowed=False, reason="max_parallel_manual")

        hourly_count = await _get_int(hourly_key)
        if hourly_count >= settings.SCREENING_MAX_PER_HOUR:
            return ProcessingQuotaDecision(allowed=False, reason="max_per_hour")

        daily_count = await _get_int(daily_key)
        if daily_count >= settings.SCREENING_MAX_PER_DAY:
            return ProcessingQuotaDecision(allowed=False, reason="max_per_day")

        processing_lock = await redis.set(
            processing_key,
            trigger_source,
            ex=settings.SCREENING_PROCESSING_LOCK_SECONDS,
            nx=True,
        )
        if not processing_lock:
            return ProcessingQuotaDecision(allowed=False, reason="already_processing")

        await redis.incr(total_counter_key)
        await redis.expire(total_counter_key, settings.SCREENING_PROCESSING_LOCK_SECONDS)
        if trigger_source == "manual":
            await redis.incr(source_counter_key)
            await redis.expire(
                source_counter_key,
                settings.SCREENING_PROCESSING_LOCK_SECONDS,
            )
        await redis.incr(hourly_key)
        await redis.expire(hourly_key, 3600)
        await redis.incr(daily_key)
        await redis.expire(daily_key, 86400)
        return ProcessingQuotaDecision(allowed=True)
    finally:
        await redis.delete(_guard_lock_key())


async def release_processing_quota(application_id: int, *, trigger_source: str) -> None:
    redis = redis_client.redis
    if not redis:
        return

    await redis.delete(_processing_lock_key(application_id))
    await _safe_decr(_parallel_counter_key("total"))
    if trigger_source == "manual":
        await _safe_decr(_parallel_counter_key("manual"))


async def _safe_decr(key: str) -> None:
    redis = redis_client.redis
    if not redis:
        return
    current = await _get_int(key)
    if current <= 0:
        await redis.delete(key)
        return
    await redis.decr(key)


async def get_recovery_retry_count(application_id: int) -> int:
    return await _get_int(_recovery_retry_key(application_id))


async def increment_recovery_retry_count(application_id: int) -> int:
    redis = redis_client.redis
    if not redis:
        return 1
    value = await redis.incr(_recovery_retry_key(application_id))
    await redis.expire(_recovery_retry_key(application_id), 7 * 86400)
    return int(value)


async def clear_recovery_retry_count(application_id: int) -> None:
    redis = redis_client.redis
    if not redis:
        return
    await redis.delete(_recovery_retry_key(application_id))
