from redis.asyncio import Redis

from app.settings import get_config
from app.tiq import broker

HEARTBEAT_KEY = "izihata:tasks:heartbeat"


@broker.task(schedule=[{"cron": "* * * * *"}])
async def worker_heartbeat() -> None:
    """Prove that the scheduler can enqueue and a worker can execute a job."""
    async with Redis.from_url(get_config().redis_url) as redis:
        await redis.set(HEARTBEAT_KEY, "ok", ex=180)
