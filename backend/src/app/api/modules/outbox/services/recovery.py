from dataclasses import dataclass

from app.api.modules.outbox.models import OutboxStatus
from app.database.uow import UnitOfWork


@dataclass(frozen=True, slots=True)
class OutboxStats:
    pending: int
    processing: int
    processed: int
    failed: int
    dead: int


class OutboxRecoveryService:
    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def get_stats(self) -> OutboxStats:
        counts = await self._uow.outbox.status_counts()
        return OutboxStats(
            pending=counts[OutboxStatus.PENDING],
            processing=counts[OutboxStatus.PROCESSING],
            processed=counts[OutboxStatus.PROCESSED],
            failed=counts[OutboxStatus.FAILED],
            dead=counts[OutboxStatus.DEAD],
        )

    async def retry_dead(self, limit: int) -> int:
        retried = await self._uow.outbox.retry_dead(limit)
        await self._uow.commit()
        return retried
