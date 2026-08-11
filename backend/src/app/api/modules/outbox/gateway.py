from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.modules.outbox.models import OutboxEvent, OutboxStatus


class OutboxGateway:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(self, topic: str, payload: dict[str, Any]) -> OutboxEvent:
        event = OutboxEvent(topic=topic, payload=payload)
        self._session.add(event)
        await self._session.flush()
        return event

    async def claim_pending(
        self,
        limit: int = 10,
        lease_seconds: int = 300,
    ) -> list[OutboxEvent]:
        now = datetime.now(UTC)
        stmt = (
            select(OutboxEvent)
            .where(
                or_(
                    (
                        OutboxEvent.status.in_(
                            [OutboxStatus.PENDING, OutboxStatus.FAILED]
                        )
                        & or_(
                            OutboxEvent.next_attempt_at.is_(None),
                            OutboxEvent.next_attempt_at <= now,
                        )
                    ),
                    (
                        (OutboxEvent.status == OutboxStatus.PROCESSING)
                        & (OutboxEvent.locked_until <= now)
                    ),
                ),
            )
            .order_by(OutboxEvent.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        events = list((await self._session.execute(stmt)).scalars().all())
        for event in events:
            event.status = OutboxStatus.PROCESSING
            event.locked_until = now + timedelta(seconds=lease_seconds)
        await self._session.flush()
        return events

    async def delete_processed_before(self, cutoff: datetime) -> int:
        stmt = (
            delete(OutboxEvent)
            .where(
                OutboxEvent.status == OutboxStatus.PROCESSED,
                OutboxEvent.processed_at < cutoff,
            )
            .returning(OutboxEvent.id)
        )
        result = await self._session.execute(stmt)
        return len(result.scalars().all())

    async def status_counts(self) -> dict[OutboxStatus, int]:
        stmt = select(OutboxEvent.status, func.count(OutboxEvent.id)).group_by(
            OutboxEvent.status
        )
        rows = (await self._session.execute(stmt)).all()
        counts = dict.fromkeys(OutboxStatus, 0)
        counts.update({status: int(count) for status, count in rows})
        return counts

    async def retry_dead(self, limit: int) -> int:
        stmt = (
            select(OutboxEvent)
            .where(OutboxEvent.status == OutboxStatus.DEAD)
            .order_by(OutboxEvent.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        events = list((await self._session.execute(stmt)).scalars().all())
        for event in events:
            event.status = OutboxStatus.PENDING
            event.attempts = 0
            event.next_attempt_at = None
            event.locked_until = None
            event.last_error = None
        await self._session.flush()
        return len(events)
