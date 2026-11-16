"""Bounded cache for public address lookups, with a short outage fallback."""

import asyncio
import logging
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from time import monotonic
from weakref import WeakValueDictionary

from app.api.common.exceptions import ServiceUnavailableError

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class LookupEntry[T]:
    items: tuple[T, ...]
    fresh_until: float
    usable_until: float


class LookupCache[T]:
    def __init__(self, *, capacity: int = 128, ttl: int = 300, stale_ttl: int = 900):
        self._capacity = capacity
        self._ttl = ttl
        self._stale_ttl = stale_ttl
        self._entries: OrderedDict[str, LookupEntry[T]] = OrderedDict()
        self._locks: WeakValueDictionary[str, asyncio.Lock] = WeakValueDictionary()

    async def remember(
        self, key: str, load: Callable[[], Awaitable[list[T]]]
    ) -> list[T]:
        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            cached = self._entries.get(key)
            if cached and cached.fresh_until > monotonic():
                self._entries.move_to_end(key)
                return list(cached.items)
            try:
                items = await load()
            except ServiceUnavailableError:
                if cached and cached.usable_until > monotonic():
                    logger.warning("Using recent address lookup during provider outage")
                    return list(cached.items)
                raise
            now = monotonic()
            self._entries[key] = LookupEntry(
                tuple(items), now + self._ttl, now + self._ttl + self._stale_ttl
            )
            self._entries.move_to_end(key)
            while len(self._entries) > self._capacity:
                self._entries.popitem(last=False)
            return list(items)
