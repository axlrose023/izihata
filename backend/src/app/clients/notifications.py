import logging
from typing import Protocol

from app.api.modules.outbox.models import OutboxEvent
from app.settings import Config

logger = logging.getLogger(__name__)


class EventDispatcher(Protocol):
    async def dispatch(self, event: OutboxEvent) -> None: ...


class NotificationDispatcher:
    """Adapter seam for CRM, SMS, email, or messenger integrations."""

    def __init__(self, config: Config):
        self._environment = config.env

    async def dispatch(self, event: OutboxEvent) -> None:
        if self._environment == "prod":
            raise RuntimeError("Production notification adapter is not configured")
        logger.info(
            "Dispatching domain notification",
            extra={
                "event_id": str(event.id),
                "topic": event.topic,
                "payload": event.payload,
            },
        )
