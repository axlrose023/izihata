import asyncio

from redis.asyncio import Redis

from app.settings import get_config
from app.tasks.heartbeat import HEARTBEAT_KEY


async def is_healthy() -> bool:
    async with Redis.from_url(get_config().redis_url) as redis:
        return bool(await redis.exists(HEARTBEAT_KEY))


if __name__ == "__main__":
    raise SystemExit(0 if asyncio.run(is_healthy()) else 1)
