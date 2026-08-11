import asyncio
import logging
from datetime import UTC, datetime, timedelta

from app.api.modules.outbox.models import OutboxEvent, OutboxStatus
from app.clients.notifications import EventDispatcher

logger = logging.getLogger(__name__)


class OutboxDeliveryService:
    def __init__(
        self,
        dispatcher: EventDispatcher,
        timeout_seconds: float = 15,
        max_attempts: int = 8,
    ):
        self._dispatcher = dispatcher
        self._timeout_seconds = timeout_seconds
        self._max_attempts = max_attempts

    async def deliver(self, event: OutboxEvent) -> None:
        try:
            async with asyncio.timeout(self._timeout_seconds):
                await self._dispatcher.dispatch(event)
        except Exception as exc:
            event.attempts = (event.attempts or 0) + 1
            event.last_error = str(exc)[:2000]
            event.locked_until = None
            if event.attempts >= self._max_attempts:
                event.status = OutboxStatus.DEAD
                event.next_attempt_at = None
                logger.exception("Outbox event exhausted delivery attempts")
            else:
                event.status = OutboxStatus.FAILED
                delay_minutes = min(2**event.attempts, 60)
                event.next_attempt_at = datetime.now(UTC) + timedelta(
                    minutes=delay_minutes
                )
                logger.exception("Outbox event dispatch failed")
        else:
            event.attempts = (event.attempts or 0) + 1
            event.status = OutboxStatus.PROCESSED
            event.processed_at = datetime.now(UTC)
            event.next_attempt_at = None
            event.locked_until = None
            event.last_error = None
