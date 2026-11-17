"""Redis snapshots and bounded, coalesced fallback lookups."""

import asyncio
import logging
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from contextlib import suppress
from time import monotonic, time
from typing import Any, Self
from uuid import uuid4
from weakref import WeakValueDictionary

from pydantic import BaseModel, ConfigDict, ValidationError
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.api.common.exceptions import ServiceUnavailableError
from app.clients.nova_poshta_gate import directory_unavailable

logger = logging.getLogger(__name__)
_RELEASE = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
    return redis.call('DEL', KEYS[1])
end
return 0
"""
_SAVE_QUERY = """
redis.call('SET', KEYS[1], ARGV[1], 'EX', ARGV[2])
redis.call('ZADD', KEYS[2], ARGV[3], KEYS[1])
if redis.call('TTL', KEYS[2]) < tonumber(ARGV[2]) then
    redis.call('EXPIRE', KEYS[2], ARGV[2])
end
local excess = redis.call('ZCARD', KEYS[2]) - 512
if excess > 0 then
    local old = redis.call('ZRANGE', KEYS[2], 0, excess - 1)
    for _, key in ipairs(old) do
        redis.call('DEL', key)
        redis.call('ZREM', KEYS[2], key)
    end
end
"""


class DirectorySnapshot[T](BaseModel):
    items: tuple[T, ...]
    fresh_until: float
    expires_at: float

    model_config = ConfigDict(frozen=True, extra="forbid")

    @classmethod
    def create(cls, items: list[T], *, ttl: int, stale: int) -> Self:
        now = time()
        return cls(
            items=tuple(items), fresh_until=now + ttl, expires_at=now + ttl + stale
        )

    @property
    def version(self) -> tuple[float, float]:
        # Timestamps are set once, when a complete snapshot is published.
        return self.fresh_until, self.expires_at

    @property
    def is_fresh(self) -> bool:
        return self.fresh_until > time()


class DeliveryDirectoryCache:
    def __init__(self, redis: Redis, *, namespace: str = "izihata:delivery:v1"):
        self._redis = redis
        self.namespace = namespace
        self._local: OrderedDict[str, tuple[float, DirectorySnapshot[Any]]] = (
            OrderedDict()
        )
        self._read_locks: WeakValueDictionary[str, asyncio.Lock] = WeakValueDictionary()
        self._load_locks: WeakValueDictionary[str, asyncio.Lock] = WeakValueDictionary()

    async def read[T: DirectorySnapshot](
        self, key: str, model: type[T], *, refresh: bool = False
    ) -> T | None:
        async with self._read_locks.setdefault(key, asyncio.Lock()):
            local = self._local.get(key)
            if (
                not refresh
                and local
                and local[0] > monotonic()
                and local[1].expires_at > time()
            ):
                self._local.move_to_end(key)
                return model.model_validate(local[1])
            try:
                raw = await self._redis.get(f"{self.namespace}:{key}")
            except RedisError as exc:
                raise directory_unavailable() from exc
            if raw is None:
                return None
            try:
                value = await asyncio.to_thread(model.model_validate_json, raw)
            except ValidationError:
                logger.warning("Invalid cached delivery directory; loading again")
                return None
            if value.expires_at <= time():
                return None
            if local and local[1].version == value.version:
                value = model.model_validate(local[1])
            self._remember_local(key, value)
            return value

    def _remember_local(self, key: str, value: DirectorySnapshot) -> None:
        self._local[key] = (monotonic() + 30, value)
        self._local.move_to_end(key)
        while len(self._local) > 64:
            self._local.popitem(last=False)

    async def save(self, key: str, value: DirectorySnapshot) -> None:
        raw = await asyncio.to_thread(value.model_dump_json)
        ttl = max(1, int(value.expires_at - time()))
        try:
            if key.startswith("query:"):
                await self._redis.eval(
                    _SAVE_QUERY,
                    2,
                    f"{self.namespace}:{key}",
                    f"{self.namespace}:index:queries",
                    raw,
                    ttl,
                    time(),
                )
            else:
                await self._redis.set(f"{self.namespace}:{key}", raw, ex=ttl)
        except RedisError as exc:
            raise directory_unavailable() from exc
        self._remember_local(key, value)

    async def claim(self, key: str, *, seconds: int) -> str | None:
        token = uuid4().hex
        try:
            acquired = await self._redis.set(
                f"{self.namespace}:lock:{key}", token, nx=True, ex=seconds
            )
        except RedisError as exc:
            raise directory_unavailable() from exc
        return token if acquired else None

    async def release(self, key: str, token: str) -> None:
        with suppress(RedisError):
            await self._redis.eval(_RELEASE, 1, f"{self.namespace}:lock:{key}", token)

    async def remember[T: DirectorySnapshot](
        self, key: str, model: type[T], load: Callable[[], Awaitable[T]]
    ) -> T:
        async with self._load_locks.setdefault(key, asyncio.Lock()):
            cached = await self.read(key, model)
            if cached and cached.is_fresh:
                return cached
            deadline = monotonic() + 8
            while True:
                token = await self.claim(f"lookup:{key}", seconds=10)
                if token:
                    try:
                        latest = await self.read(key, model, refresh=True)
                        if latest and latest.is_fresh:
                            return latest
                        value = await load()
                        await self.save(key, value)
                        return value
                    except ServiceUnavailableError:
                        if not cached or cached.expires_at <= time():
                            raise
                        grace = cached.model_copy(
                            update={"fresh_until": min(time() + 10, cached.expires_at)}
                        )
                        with suppress(ServiceUnavailableError):
                            await self.save(key, grace)
                        return grace
                    finally:
                        await self.release(f"lookup:{key}", token)
                if cached:
                    return cached
                if monotonic() >= deadline:
                    raise directory_unavailable()
                await asyncio.sleep(0.05)
                latest = await self.read(key, model)
                if latest:
                    return latest
