from types import SimpleNamespace
from typing import cast

import pytest

from app.api.modules.outbox.models import OutboxEvent
from app.clients.notifications import NotificationDispatcher
from app.settings import Config


@pytest.mark.asyncio
async def test_production_logging_adapter_never_marks_delivery_as_real():
    config = cast(Config, SimpleNamespace(env="prod"))
    dispatcher = NotificationDispatcher(config)

    with pytest.raises(RuntimeError, match="not configured"):
        await dispatcher.dispatch(OutboxEvent(topic="test", payload={}))
