import logging
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.api.modules.outbox.models import OutboxEvent
from app.api.modules.outbox.service import OutboxDeliveryService, OutboxRecoveryService
from app.clients.notifications import NotificationDispatcher
from app.database.engine import SessionFactory
from app.database.uow import UnitOfWork
from app.settings import get_config
from app.tiq import broker

logger = logging.getLogger(__name__)


@broker.task(schedule=[{"cron": "* * * * *"}])
async def dispatch_outbox() -> None:
    config = get_config()
    delivery_service = OutboxDeliveryService(
        NotificationDispatcher(config),
        timeout_seconds=config.outbox.dispatch_timeout_seconds,
        max_attempts=config.outbox.max_attempts,
    )
    async with SessionFactory() as session, UnitOfWork(session) as uow:
        events = await uow.outbox.claim_pending(
            limit=config.outbox.batch_size,
            lease_seconds=config.outbox.lease_seconds,
        )
        await uow.commit()
        for event in events:
            delivered = await delivery_service.deliver(event)
            if delivered:
                await _mark_delivered_stock_subscription(event, uow)
            await uow.commit()
        if events:
            stats = await OutboxRecoveryService(uow).get_stats()
            logger.info(
                "Outbox batch completed",
                extra={"claimed": len(events), "status_counts": asdict(stats)},
            )


async def _mark_delivered_stock_subscription(
    event: OutboxEvent,
    uow: UnitOfWork,
) -> None:
    if event.topic != "catalog.back_in_stock":
        return
    subscription_id = event.payload.get("subscription_id")
    if not isinstance(subscription_id, str):
        logger.error("Stock notification event has no valid subscription id")
        return
    try:
        parsed_id = UUID(subscription_id)
    except ValueError:
        logger.error("Stock notification event has an invalid subscription id")
        return
    await uow.products.mark_stock_subscription_notified(parsed_id)


@broker.task(schedule=[{"cron": "0 3 * * *"}])
async def cleanup_outbox() -> None:
    config = get_config()
    cutoff = datetime.now(UTC) - timedelta(days=config.outbox.retention_days)
    async with SessionFactory() as session, UnitOfWork(session) as uow:
        await uow.outbox.delete_processed_before(cutoff)
        await uow.commit()
