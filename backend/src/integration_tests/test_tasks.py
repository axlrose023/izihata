import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.api.modules.auth.models import AuthSession
from app.api.modules.outbox.models import OutboxEvent, OutboxStatus
from app.api.modules.users.models import User
from app.database.engine import SessionFactory
from app.database.uow import UnitOfWork
from app.tasks import cleanup_auth_sessions, cleanup_outbox, dispatch_outbox

pytestmark = pytest.mark.integration


@pytest.mark.asyncio(loop_scope="session")
async def test_dispatch_task_processes_claimed_event():
    async with SessionFactory() as session, UnitOfWork(session) as uow:
        event = await uow.outbox.add("integration.task", {"id": "test"})
        event_id = event.id
        await uow.commit()

    await dispatch_outbox.original_func()

    async with SessionFactory() as session:
        processed = await session.get(OutboxEvent, event_id)
        assert processed is not None
        assert processed.status == OutboxStatus.PROCESSED


@pytest.mark.asyncio(loop_scope="session")
async def test_cleanup_tasks_remove_expired_rows():
    now = datetime.now(UTC)
    async with SessionFactory() as session, UnitOfWork(session) as uow:
        user = User(
            username=f"task-cleanup-{uuid.uuid4()}",
            password_hash=uuid.uuid4().hex,
            is_active=True,
        )
        await uow.users.create(user)
        auth_session = AuthSession(
            user_id=user.id,
            refresh_jti=uuid.uuid4(),
            expires_at=now - timedelta(seconds=1),
        )
        old_event = OutboxEvent(
            topic="integration.cleanup",
            payload={},
            status=OutboxStatus.PROCESSED,
            processed_at=now - timedelta(days=31),
        )
        session.add_all([auth_session, old_event])
        await uow.commit()
        auth_session_id = auth_session.id
        old_event_id = old_event.id

    await cleanup_auth_sessions.original_func()
    await cleanup_outbox.original_func()

    async with SessionFactory() as session:
        assert await session.get(AuthSession, auth_session_id) is None
        assert await session.get(OutboxEvent, old_event_id) is None
