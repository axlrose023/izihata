import asyncio

import pytest

from app.api.common.exceptions import ServiceUnavailableError
from app.clients.lookup_cache import LookupCache


@pytest.mark.asyncio
async def test_coalesces_identical_lookups_and_returns_independent_lists():
    cache: LookupCache[str] = LookupCache()
    calls = 0

    async def load():
        nonlocal calls
        calls += 1
        await asyncio.sleep(0)
        return ["City"]

    results = await asyncio.gather(*(cache.remember("city", load) for _ in range(5)))
    assert calls == 1
    results[0].clear()
    assert await cache.remember("city", load) == ["City"]


@pytest.mark.asyncio
async def test_uses_recent_success_during_outage_but_not_expired_data(monkeypatch):
    now = 0
    monkeypatch.setattr("app.clients.lookup_cache.monotonic", lambda: now)
    cache: LookupCache[str] = LookupCache(ttl=10, stale_ttl=20)

    async def load():
        return ["City"]

    async def fail():
        raise ServiceUnavailableError("Unavailable")

    await cache.remember("city", load)
    now = 11
    assert await cache.remember("city", fail) == ["City"]
    now = 31
    with pytest.raises(ServiceUnavailableError):
        await cache.remember("city", fail)


@pytest.mark.asyncio
async def test_evicts_least_recent_lookup_and_does_not_cache_failures():
    cache: LookupCache[str] = LookupCache(capacity=1)

    async def load():
        return ["City"]

    async def fail():
        raise ServiceUnavailableError("Unavailable")

    await cache.remember("a", load)
    await cache.remember("b", load)
    with pytest.raises(ServiceUnavailableError):
        await cache.remember("a", fail)
    assert await cache.remember("a", load) == ["City"]
