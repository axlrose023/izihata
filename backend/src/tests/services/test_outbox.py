import asyncio

import pytest

from app.api.modules.outbox.models import OutboxEvent, OutboxStatus
from app.api.modules.outbox.service import OutboxDeliveryService


class SuccessfulDispatcher:
    async def dispatch(self, event: OutboxEvent) -> None:
        return None


class FailingDispatcher:
    async def dispatch(self, event: OutboxEvent) -> None:
        raise RuntimeError("provider unavailable")


class SlowDispatcher:
    async def dispatch(self, event: OutboxEvent) -> None:
        await asyncio.sleep(1)


@pytest.mark.asyncio
async def test_marks_outbox_event_as_processed():
    event = OutboxEvent(topic="test", payload={})
    service = OutboxDeliveryService(SuccessfulDispatcher())

    await service.deliver(event)

    assert event.status == OutboxStatus.PROCESSED
    assert event.attempts == 1
    assert event.processed_at is not None
    assert event.locked_until is None


@pytest.mark.asyncio
async def test_schedules_failed_outbox_event_for_retry():
    event = OutboxEvent(topic="test", payload={})
    service = OutboxDeliveryService(FailingDispatcher())

    await service.deliver(event)

    assert event.status == OutboxStatus.FAILED
    assert event.attempts == 1
    assert event.next_attempt_at is not None
    assert event.last_error == "provider unavailable"


@pytest.mark.asyncio
async def test_moves_outbox_event_to_dead_letter_after_max_attempts():
    event = OutboxEvent(topic="test", payload={}, attempts=2)
    service = OutboxDeliveryService(FailingDispatcher(), max_attempts=3)

    await service.deliver(event)

    assert event.status == OutboxStatus.DEAD
    assert event.attempts == 3
    assert event.next_attempt_at is None


@pytest.mark.asyncio
async def test_times_out_slow_dispatcher_and_schedules_retry():
    event = OutboxEvent(topic="test", payload={})
    service = OutboxDeliveryService(SlowDispatcher(), timeout_seconds=0.001)

    await service.deliver(event)

    assert event.status == OutboxStatus.FAILED
    assert event.attempts == 1
    assert event.next_attempt_at is not None
