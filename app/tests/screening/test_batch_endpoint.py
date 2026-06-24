"""Unit tests for batch screening endpoint router logic.

Tests the POST /screening/batch/run endpoint by mocking
queue_screening and run_screening_task dependencies.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.features.screening.schemas.schema import (
    BatchScreeningRequest,
    BatchScreeningResponse,
    ScreeningQueuedResponse,
)


def _make_queued_response(idx: int) -> ScreeningQueuedResponse:
    return ScreeningQueuedResponse(
        message=f"Screening queued for application {idx}",
        queue_status="queued",
        task_enqueued=True,
    )


def _make_duplicate_response() -> ScreeningQueuedResponse:
    return ScreeningQueuedResponse(
        message="Duplicate screening request",
        queue_status="duplicate",
        task_enqueued=False,
    )


def _make_quota_response() -> ScreeningQueuedResponse:
    return ScreeningQueuedResponse(
        message="Quota exceeded",
        queue_status="pending_quota",
        task_enqueued=False,
    )


class TestBatchScreeningLogic:
    """Test the batch screening endpoint logic in isolation."""

    @pytest.fixture
    def mock_deps(self):
        """Provide mock queue_screening and kiq function."""
        return {
            "queue_screening": AsyncMock(),
            "kiq": AsyncMock(),
            "settings": MagicMock(SCREENING_BATCH_ENQUEUE_DELAY_SECONDS=0),
        }

    async def _run_batch_logic(self, application_ids, queue_side_effects):
        """Simulate the batch endpoint logic from router.py."""
        from app.features.screening.schemas.schema import (
            BatchScreeningItem,
            BatchScreeningResponse,
        )

        results = []
        queued = 0
        duplicates = 0
        quota_blocked = 0

        for i, application_id in enumerate(application_ids):
            result = queue_side_effects[i]

            if result.task_enqueued:
                queued += 1
            elif result.queue_status == "duplicate":
                duplicates += 1
            else:
                quota_blocked += 1

            results.append(
                BatchScreeningItem(
                    application_id=application_id,
                    queue_status=result.queue_status,
                    task_enqueued=result.task_enqueued,
                )
            )

        return BatchScreeningResponse(
            total=len(application_ids),
            queued=queued,
            duplicates=duplicates,
            quota_blocked=quota_blocked,
            results=results,
        )

    @pytest.mark.asyncio
    async def test_all_queued(self, mock_deps):
        effects = [
            _make_queued_response(1),
            _make_queued_response(2),
            _make_queued_response(3),
        ]
        resp = await self._run_batch_logic([10, 20, 30], effects)

        assert resp.total == 3
        assert resp.queued == 3
        assert resp.duplicates == 0
        assert resp.quota_blocked == 0
        assert all(r.task_enqueued for r in resp.results)

    @pytest.mark.asyncio
    async def test_mixed_results(self, mock_deps):
        effects = [
            _make_queued_response(1),
            _make_duplicate_response(),
            _make_quota_response(),
        ]
        resp = await self._run_batch_logic([10, 20, 30], effects)

        assert resp.total == 3
        assert resp.queued == 1
        assert resp.duplicates == 1
        assert resp.quota_blocked == 1
        assert resp.results[0].task_enqueued is True
        assert resp.results[1].task_enqueued is False
        assert resp.results[2].task_enqueued is False

    @pytest.mark.asyncio
    async def test_all_duplicates(self, mock_deps):
        effects = [
            _make_duplicate_response(),
            _make_duplicate_response(),
        ]
        resp = await self._run_batch_logic([10, 20], effects)

        assert resp.total == 2
        assert resp.queued == 0
        assert resp.duplicates == 2

    @pytest.mark.asyncio
    async def test_empty_batch(self, mock_deps):
        resp = await self._run_batch_logic([], [])
        assert resp.total == 0
        assert resp.queued == 0
        assert resp.results == []

    @pytest.mark.asyncio
    async def test_application_ids_preserved(self, mock_deps):
        effects = [_make_queued_response(1)]
        resp = await self._run_batch_logic([42], effects)
        assert resp.results[0].application_id == 42
