from datetime import UTC, datetime

from app.database.engine import SessionFactory
from app.database.uow import UnitOfWork
from app.tiq import broker


@broker.task(schedule=[{"cron": "15 3 * * *"}])
async def cleanup_auth_sessions() -> None:
    async with SessionFactory() as session, UnitOfWork(session) as uow:
        now = datetime.now(UTC)
        await uow.auth_sessions.delete_expired(now)
        await uow.customers.delete_expired_sessions(now)
        await uow.commit()
