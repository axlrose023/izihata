"""One provider-key budget shared by web processes and background workers."""

import asyncio
import hashlib
from contextlib import suppress
from time import monotonic

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.api.common.exceptions import ServiceUnavailableError

_ACQUIRE = """
local cooldown = redis.call('PTTL', KEYS[1])
if cooldown > 0 then return cooldown end
if redis.call('SET', KEYS[2], '1', 'NX', 'PX', ARGV[1]) then return 0 end
return math.max(redis.call('PTTL', KEYS[2]), 1)
"""
_BLOCK = """
if redis.call('PTTL', KEYS[1]) < tonumber(ARGV[1]) then
    redis.call('SET', KEYS[1], '1', 'PX', ARGV[1])
end
"""


def directory_unavailable() -> ServiceUnavailableError:
    return ServiceUnavailableError(
        "Delivery address directory is temporarily unavailable",
        code="delivery_provider_unavailable",
    )


class NovaPoshtaRequestGate:
    def __init__(
        self,
        redis: Redis,
        identity: str,
        *,
        interval: float,
        max_wait: float,
    ):
        digest = hashlib.sha256(identity.encode()).hexdigest()[:24]
        self._prefix = f"izihata:nova-poshta:gate:{digest}"
        self._redis = redis
        self._interval = interval
        self._max_wait = max_wait

    async def acquire(self) -> None:
        deadline = monotonic() + self._max_wait
        try:
            while True:
                delay_ms = int(
                    await self._redis.eval(
                        _ACQUIRE,
                        2,
                        f"{self._prefix}:cooldown",
                        f"{self._prefix}:slot",
                        max(1, int(self._interval * 1000)),
                    )
                )
                if delay_ms == 0:
                    return
                remaining = deadline - monotonic()
                if remaining <= 0 or delay_ms / 1000 > remaining:
                    raise directory_unavailable()
                await asyncio.sleep(min(delay_ms / 1000 + 0.005, remaining))
        except (RedisError, TimeoutError) as exc:
            # Do not turn a Redis outage into an uncoordinated provider flood.
            raise directory_unavailable() from exc

    async def block(self, seconds: float) -> None:
        with suppress(RedisError):
            await self._redis.eval(
                _BLOCK, 1, f"{self._prefix}:cooldown", max(1, int(seconds * 1000))
            )
