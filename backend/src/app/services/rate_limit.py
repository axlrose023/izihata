import logging
from dataclasses import dataclass

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.api.common.exceptions import ServiceUnavailableError, TooManyRequestsError
from app.settings import Config

logger = logging.getLogger(__name__)

_FIXED_WINDOW_SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
local ttl = redis.call('TTL', KEYS[1])
return {current, ttl}
"""


@dataclass(frozen=True, slots=True)
class RateLimitPolicy:
    scope: str
    requests: int
    window_seconds: int


class RateLimitService:
    def __init__(self, redis: Redis, config: Config):
        self._redis = redis
        self._enabled = config.rate_limit.enabled
        self._fail_open = config.rate_limit.fail_open

    async def check(self, identity: str, policy: RateLimitPolicy) -> None:
        if not self._enabled:
            return

        key = f"izihata:rate-limit:{policy.scope}:{identity}"
        try:
            result = await self._redis.eval(
                _FIXED_WINDOW_SCRIPT,
                1,
                key,
                policy.window_seconds,
            )
            current, ttl = int(result[0]), int(result[1])
        except (RedisError, ConnectionError, TimeoutError) as exc:
            if self._fail_open:
                logger.exception("Rate limiter is unavailable; allowing request")
                return
            logger.exception("Rate limiter is unavailable; rejecting request")
            raise ServiceUnavailableError("Rate limiter is unavailable") from exc

        if current > policy.requests:
            raise TooManyRequestsError(retry_after=ttl)
