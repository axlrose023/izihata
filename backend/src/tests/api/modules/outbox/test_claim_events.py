from datetime import UTC, datetime, timedelta

import pytest

from app.api.modules.outbox.models import OutboxEvent, OutboxStatus
from app.api.modules.outbox.service import OutboxRecoveryService


@pytest.mark.asyncio
async def test_claims_outbox_event_with_processing_lease(uow):
    event = await uow.outbox.add("test.created", {"id": "test"})
    await uow.commit()

    claimed = await uow.outbox.claim_pending(limit=10_000)

    current = next(item for item in claimed if item.id == event.id)
    assert current.status == OutboxStatus.PROCESSING
    assert current.locked_until is not None


@pytest.mark.asyncio
async def test_reclaims_expired_processing_lease(uow):
    expired_lock = datetime.now(UTC) - timedelta(seconds=1)
    event = OutboxEvent(
        topic="test.expired",
        payload={},
        status=OutboxStatus.PROCESSING,
        locked_until=expired_lock,
    )
    uow.session.add(event)
    await uow.commit()

    claimed = await uow.outbox.claim_pending(limit=10_000, lease_seconds=60)

    current = next(item for item in claimed if item.id == event.id)
    assert current.status == OutboxStatus.PROCESSING
    assert current.locked_until != expired_lock


@pytest.mark.asyncio
async def test_deletes_only_expired_processed_events(uow):
    now = datetime.now(UTC)
    expired = OutboxEvent(
        topic="test.expired-processed",
        payload={},
        status=OutboxStatus.PROCESSED,
        processed_at=now - timedelta(days=31),
    )
    recent = OutboxEvent(
        topic="test.recent-processed",
        payload={},
        status=OutboxStatus.PROCESSED,
        processed_at=now,
    )
    uow.session.add_all([expired, recent])
    await uow.commit()

    deleted = await uow.outbox.delete_processed_before(now - timedelta(days=30))
    await uow.commit()

    assert deleted == 1
    assert await uow.session.get(OutboxEvent, expired.id) is None
    assert await uow.session.get(OutboxEvent, recent.id) is not None


@pytest.mark.asyncio
async def test_reports_and_retries_dead_events(uow):
    event = OutboxEvent(
        topic="test.dead",
        payload={},
        status=OutboxStatus.DEAD,
        attempts=8,
        last_error="provider unavailable",
    )
    uow.session.add(event)
    await uow.commit()
    service = OutboxRecoveryService(uow)

    before = await service.get_stats()
    retried = await service.retry_dead(limit=1)
    after = await service.get_stats()

    assert before.dead >= 1
    assert retried == 1
    assert event.status == OutboxStatus.PENDING
    assert event.attempts == 0
    assert event.last_error is None
    assert after.dead == before.dead - 1
