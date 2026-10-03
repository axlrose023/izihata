import asyncio
from unittest.mock import AsyncMock

import pytest
from pydantic import BaseModel
from redis.exceptions import ConnectionError

from app.api.modules.catalog.cache import (
    PublicCatalogCache,
    catalog_cache_key,
    commit_catalog,
)
from app.api.modules.catalog.schema import ProductListParams, SpecFacetParams


class Result(BaseModel):
    count: int


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.ttls = []

    async def get(self, key):
        return self.values.get(key)

    async def set(self, key, value, ex):
        self.values[key] = value
        self.ttls.append(ex)

    async def incr(self, key):
        self.values[key] = str(int(self.values.get(key, "0")) + 1)
        return int(self.values[key])


@pytest.mark.asyncio
async def test_cached_metadata_and_stampede_protection():
    redis = FakeRedis()
    cache = PublicCatalogCache(redis)
    calls = 0

    async def load():
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.01)
        return Result(count=4)

    results = await asyncio.gather(
        *(cache.remember("categories", Result, load) for _ in range(20))
    )
    assert calls == 1
    assert all(value.count == 4 for value in results)
    assert redis.ttls == [30]
    await cache.invalidate()
    assert (await cache.remember("categories", Result, load)).count == 4
    assert calls == 2


@pytest.mark.asyncio
async def test_corrupt_cache_is_reloaded():
    redis = FakeRedis()
    cache = PublicCatalogCache(redis)
    loader = AsyncMock(return_value=Result(count=1))
    await cache.remember("brands", Result, loader)
    for key in redis.values:
        redis.values[key] = '{"count": "broken"}'
    assert (await cache.remember("brands", Result, loader)).count == 1
    assert loader.await_count == 2


@pytest.mark.asyncio
async def test_cache_outage_falls_back_without_failing_successful_write():
    redis = AsyncMock()
    redis.get.side_effect = ConnectionError("unavailable")
    redis.incr.side_effect = ConnectionError("unavailable")
    cache = PublicCatalogCache(redis)
    loader = AsyncMock(return_value=Result(count=9))
    assert (await cache.remember("sections", Result, loader)).count == 9
    loader.assert_awaited_once()
    uow = AsyncMock()
    await commit_catalog(uow, cache)
    uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_disabled_cache_never_connects_to_redis():
    redis = AsyncMock()
    cache = PublicCatalogCache(redis, enabled=False)
    assert (
        await cache.remember("brands", Result, AsyncMock(return_value=Result(count=1)))
    ).count == 1
    await cache.invalidate()
    redis.get.assert_not_called()
    redis.incr.assert_not_called()


def test_facets_share_key_across_pages_but_spec_pages_do_not():
    assert catalog_cache_key("facets", ProductListParams(page=1)) == catalog_cache_key(
        "facets", ProductListParams(page=2)
    )
    assert catalog_cache_key(
        "spec-facets", SpecFacetParams(page=1)
    ) != catalog_cache_key("spec-facets", SpecFacetParams(page=2))


@pytest.mark.asyncio
async def test_failed_database_write_does_not_invalidate_cache():
    uow = AsyncMock()
    uow.commit.side_effect = RuntimeError("rollback")
    cache = AsyncMock()
    with pytest.raises(RuntimeError):
        await commit_catalog(uow, cache)
    cache.invalidate.assert_not_awaited()


@pytest.mark.asyncio
async def test_sitemap_cache_reuses_xml_and_invalidates_with_catalog(uow):
    from app.api.modules.catalog.services.catalog_query import CatalogQueryService

    cache = PublicCatalogCache(FakeRedis())
    service = CatalogQueryService(uow, "https://example.com", cache)
    service._load_sitemap = AsyncMock(wraps=service._load_sitemap)
    first = await service.get_sitemap()
    assert "/products/" in first
    assert "https://example.com/catalog/categories" in first
    assert await service.get_sitemap() == first
    service._load_sitemap.assert_awaited_once()
    await cache.invalidate()
    assert await service.get_sitemap() == first
    assert service._load_sitemap.await_count == 2
    other_origin = CatalogQueryService(uow, "https://other.example.com", cache)
    assert "https://other.example.com/products/" in await other_origin.get_sitemap()
