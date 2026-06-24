"""Unit tests for batch screening schemas."""

import pytest
from app.features.screening.schemas.schema import (
    BatchScreeningItem,
    BatchScreeningRequest,
    BatchScreeningResponse,
)


class TestBatchScreeningRequest:
    def test_valid_request(self):
        req = BatchScreeningRequest(application_ids=[1, 2, 3])
        assert req.application_ids == [1, 2, 3]

    def test_empty_ids(self):
        req = BatchScreeningRequest(application_ids=[])
        assert req.application_ids == []

    def test_single_id(self):
        req = BatchScreeningRequest(application_ids=[42])
        assert req.application_ids == [42]

    def test_rejects_non_integer(self):
        with pytest.raises(Exception):
            BatchScreeningRequest(application_ids=["not_an_int"])


class TestBatchScreeningItem:
    def test_queued_item(self):
        item = BatchScreeningItem(
            application_id=1, queue_status="queued", task_enqueued=True
        )
        assert item.application_id == 1
        assert item.queue_status == "queued"
        assert item.task_enqueued is True

    def test_duplicate_item(self):
        item = BatchScreeningItem(
            application_id=5, queue_status="duplicate", task_enqueued=False
        )
        assert item.queue_status == "duplicate"
        assert item.task_enqueued is False

    def test_quota_blocked_item(self):
        item = BatchScreeningItem(
            application_id=9, queue_status="pending_quota", task_enqueued=False
        )
        assert item.queue_status == "pending_quota"


class TestBatchScreeningResponse:
    def test_full_response(self):
        resp = BatchScreeningResponse(
            total=3,
            queued=2,
            duplicates=1,
            quota_blocked=0,
            results=[
                BatchScreeningItem(application_id=1, queue_status="queued", task_enqueued=True),
                BatchScreeningItem(application_id=2, queue_status="queued", task_enqueued=True),
                BatchScreeningItem(application_id=3, queue_status="duplicate", task_enqueued=False),
            ],
        )
        assert resp.total == 3
        assert resp.queued == 2
        assert resp.duplicates == 1
        assert resp.quota_blocked == 0
        assert len(resp.results) == 3

    def test_all_quota_blocked(self):
        resp = BatchScreeningResponse(
            total=2,
            queued=0,
            duplicates=0,
            quota_blocked=2,
            results=[
                BatchScreeningItem(application_id=1, queue_status="pending_quota", task_enqueued=False),
                BatchScreeningItem(application_id=2, queue_status="pending_quota", task_enqueued=False),
            ],
        )
        assert resp.queued == 0
        assert resp.quota_blocked == 2
