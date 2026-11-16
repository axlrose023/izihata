import asyncio
import json
from time import perf_counter
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from dishka import Provider, Scope, make_async_container, provide
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis

from app.api.common.rate_limit import DELIVERY_LOOKUP_RATE_LIMIT
from app.api.modules.delivery.cache import DeliveryDirectoryCache
from app.api.modules.delivery.services.directory import (
    DeliveryDirectoryService,
    PointSnapshot,
)
from app.application import get_production_app
from app.clients.nova_poshta import NovaPoshtaCity, NovaPoshtaClient, NovaPoshtaPoint
from app.ioc import AppProvider, ServicesProvider
from app.settings import get_config

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio(loop_scope="session"),
]


async def test_delivery_http_uses_shared_cache_and_still_throttles_abuse(monkeypatch):
    config = get_config()
    redis = Redis.from_url(config.redis_url, decode_responses=True)
    identity = "198.51.100.242"
    query = f"інтеграція-{uuid4().hex}"
    rate_key = f"izihata:rate-limit:{DELIVERY_LOOKUP_RATE_LIMIT.scope}:{identity}"
    cache_key = "izihata:delivery:v1:" + DeliveryDirectoryService._query_key(
        "cities", query
    )
    calls = 0

    async def provider_search(provider, search):
        nonlocal calls
        calls += 1
        assert search == query
        return [NovaPoshtaCity(str(uuid4()), query, query)]

    monkeypatch.setattr(NovaPoshtaClient, "search_cities", provider_search)
    await redis.delete(rate_key)
    app = get_production_app()
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app, client=(identity, 5000)),
            base_url="http://localhost",
        ) as client:
            for _ in range(DELIVERY_LOOKUP_RATE_LIMIT.requests):
                response = await client.get(
                    "/api/v1/delivery/cities", params={"search": query}
                )
                assert response.status_code == 200, response.text
                assert response.json()[0]["name"] == query
            blocked = await client.get(
                "/api/v1/delivery/cities", params={"search": query}
            )
        assert blocked.status_code == 429
        assert int(blocked.headers["Retry-After"]) > 0
        assert calls == 1
    finally:
        await app.state.dishka_container.close()
        await redis.delete(rate_key, cache_key)
        await redis.zrem("izihata:delivery:v1:index:queries", cache_key)
        await redis.aclose()


@pytest.mark.load
async def test_500_concurrent_http_users_search_without_calling_the_provider(
    monkeypatch,
):
    import app.application

    redis = Redis.from_url(get_config().redis_url, decode_responses=True)
    namespace = f"integration:http-delivery:{uuid4().hex}"
    cache = DeliveryDirectoryCache(redis, namespace=namespace)
    provider = AsyncMock(spec=NovaPoshtaClient)
    city_refs = [str(uuid4()) for _ in range(500)]
    await cache.save(
        "points",
        PointSnapshot.create(
            [
                NovaPoshtaPoint(
                    str(index),
                    f"Відділення №{index}",
                    "",
                    str(index),
                    "branch",
                    city_ref=city_refs[(index - 1) % 500],
                )
                for index in range(1, 10001)
            ],
            ttl=300,
            stale=300,
        ),
        group="points",
    )

    class Overrides(Provider):
        @provide(scope=Scope.APP, override=True)
        def get_cache(self) -> DeliveryDirectoryCache:
            return cache

        @provide(scope=Scope.APP, override=True)
        def get_provider(self) -> NovaPoshtaClient:
            return provider

    container = make_async_container(AppProvider(), ServicesProvider(), Overrides())
    monkeypatch.setattr(app.application, "get_async_container", lambda: container)
    app = get_production_app()
    durations = []
    identities = [f"198.18.{index // 254}.{index % 254 + 1}" for index in range(500)]

    async def request(index):
        started = perf_counter()
        async with AsyncClient(
            transport=ASGITransport(app=app, client=(identities[index], 5000)),
            base_url="http://localhost",
        ) as client:
            response = await client.get(
                "/api/v1/delivery/points",
                params={
                    "city_ref": city_refs[index],
                    "kind": "branch",
                    "search": str(index + 1),
                    "page": 1,
                },
            )
        durations.append((perf_counter() - started) * 1000)
        assert response.status_code == 200, response.text
        assert response.json()["items"][0]["number"] == str(index + 1)

    try:
        results = await asyncio.gather(
            *(request(index) for index in range(500)), return_exceptions=True
        )
        errors = [result for result in results if isinstance(result, BaseException)]
        assert not errors, errors[:3]
        provider.search_points.assert_not_awaited()
        print(
            json.dumps(
                {
                    "scenario": "500 ASGI HTTP requests from 500 IPs across 500 cities, real Redis",
                    "status_200": 500,
                    "provider_calls": 0,
                    "p95_ms": round(sorted(durations)[474], 2),
                }
            )
        )
    finally:
        await container.close()
        keys = [key async for key in redis.scan_iter(match=f"{namespace}:*")]
        keys.extend(
            f"izihata:rate-limit:{DELIVERY_LOOKUP_RATE_LIMIT.scope}:{identity}"
            for identity in identities
        )
        if keys:
            await redis.delete(*keys)
        await redis.aclose()
