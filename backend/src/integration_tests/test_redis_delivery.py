import asyncio
import json
from time import monotonic, perf_counter, time
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio
from redis.asyncio import Redis

from app.api.common.exceptions import ServiceUnavailableError
from app.api.modules.delivery.cache import DeliveryDirectoryCache
from app.api.modules.delivery.enums import NOVA_POSHTA_LOCKER_TYPE_REF
from app.api.modules.delivery.services.directory import (
    CitySnapshot,
    DeliveryDirectoryService,
    PointSnapshot,
)
from app.api.modules.delivery.services.refresh import DeliveryDirectoryRefreshService
from app.clients.nova_poshta import NovaPoshtaCity, NovaPoshtaClient, NovaPoshtaPoint
from app.clients.nova_poshta_gate import NovaPoshtaRequestGate
from app.settings import NovaPoshtaConfig, get_config

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio(loop_scope="session"),
]


def _point(*args, **kwargs):
    kwargs.setdefault("city_ref", "city")
    return NovaPoshtaPoint(*args, **kwargs)


@pytest_asyncio.fixture(loop_scope="session")
async def directories():
    redis = Redis.from_url(get_config().redis_url, decode_responses=True)
    namespace = f"integration:delivery:{uuid4().hex}"
    caches = [DeliveryDirectoryCache(redis, namespace=namespace) for _ in range(4)]
    try:
        await redis.ping()
        yield redis, caches, namespace
    finally:
        keys = [key async for key in redis.scan_iter(match=f"{namespace}:*")]
        if keys:
            await redis.delete(*keys)
        await redis.aclose()


async def test_cold_lookup_is_coalesced_across_four_instances(directories):
    _, caches, _ = directories
    calls = 0

    async def load():
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.02)
        return CitySnapshot.create(
            [NovaPoshtaCity("city", "Київ", "м. Київ")], ttl=300, stale=900
        )

    results = await asyncio.gather(
        *(
            caches[index % 4].remember("query:kyiv", CitySnapshot, load)
            for index in range(200)
        )
    )
    assert calls == 1
    assert all(result.items[0].ref == "city" for result in results)


async def test_many_different_cities_use_one_network_snapshot(directories):
    _, caches, _ = directories
    points = [
        _point(
            f"point-{number}",
            f"Відділення №{number}",
            f"вул. Тестова, {number}",
            str(number),
            "branch",
            city_ref=f"city-{number % 500}",
        )
        for number in range(1, 10001)
    ]
    await caches[0].save(
        "points",
        PointSnapshot.create(points, ttl=3600, stale=86400),
        group="points",
    )
    client = AsyncMock(spec=NovaPoshtaClient)
    services = [
        DeliveryDirectoryService(client, cache, NovaPoshtaConfig()) for cache in caches
    ]
    durations = []

    async def search(index):
        started = perf_counter()
        result = await services[index % 4].search_points(
            f"city-{(index + 1) % 500}", str(index + 1)
        )
        durations.append((perf_counter() - started) * 1000)
        assert len(result) == 1 and result[0].number == str(index + 1)

    started = perf_counter()
    await asyncio.gather(*(search(index) for index in range(500)))
    ordered = sorted(durations)
    print(
        json.dumps(
            {
                "scenario": "500 concurrent searches across 500 cities; 4 instances; 10000 points",
                "elapsed_ms": round((perf_counter() - started) * 1000, 2),
                "p50_ms": round(ordered[len(ordered) // 2], 2),
                "p95_ms": round(ordered[int(len(ordered) * 0.95)], 2),
                "provider_calls": client.search_points.await_count,
            }
        )
    )
    client.search_points.assert_not_awaited()


async def test_many_city_searches_use_a_precomputed_local_index(directories):
    _, caches, _ = directories
    cities = [
        NovaPoshtaCity(str(index), f"Місто {index}", f"Місто {index}, область")
        for index in range(10000)
    ]
    await caches[0].save(
        "cities",
        CitySnapshot.create(cities, ttl=43200, stale=86400),
        group="cities",
        capacity=1,
    )
    client = AsyncMock(spec=NovaPoshtaClient)
    services = [
        DeliveryDirectoryService(client, cache, NovaPoshtaConfig()) for cache in caches
    ]
    started = perf_counter()
    results = await asyncio.gather(
        *(
            services[index % 4].search_cities(f"Місто {index % 100}")
            for index in range(500)
        )
    )
    assert all(
        items[0].name == f"Місто {index % 100}" for index, items in enumerate(results)
    )
    client.search_cities.assert_not_awaited()
    print(
        json.dumps(
            {
                "scenario": "500 concurrent city searches; 4 instances; 10000 cities",
                "elapsed_ms": round((perf_counter() - started) * 1000, 2),
                "provider_calls": 0,
            }
        )
    )


async def test_stale_directory_remains_usable_and_refresh_is_queued_once(directories):
    _, caches, _ = directories
    await caches[0].save(
        "points",
        PointSnapshot(
            items=(_point("p", "Відділення №1", "", "1", "branch"),),
            fresh_until=time() - 10,
            expires_at=time() + 300,
        ),
        group="points",
    )
    enqueue = AsyncMock()
    services = [
        DeliveryDirectoryService(
            AsyncMock(spec=NovaPoshtaClient), cache, NovaPoshtaConfig(), enqueue
        )
        for cache in caches
    ]
    results = await asyncio.gather(
        *(services[index % 4].search_points("city", "1") for index in range(100))
    )
    assert all(result[0].ref == "p" for result in results)
    enqueue.assert_awaited_once()


async def test_refresh_failure_does_not_publish_partial_pages(directories):
    _, caches, _ = directories
    original = PointSnapshot.create(
        [_point("old", "Старе відділення", "", "1", "branch")],
        ttl=3600,
        stale=86400,
    )
    await caches[0].save("points", original, group="points")
    client = AsyncMock(spec=NovaPoshtaClient)
    client.get_points_page.side_effect = [
        ([_point("new", "Нове відділення", "", "2", "branch")], True),
        ServiceUnavailableError("Provider down"),
    ]
    refresh = DeliveryDirectoryRefreshService(client, caches[0], NovaPoshtaConfig())
    with pytest.raises(ServiceUnavailableError):
        await refresh.refresh_points(force=True)
    snapshot = await caches[1].read("points", PointSnapshot)
    assert snapshot is not None and snapshot.items[0].ref == "old"
    assert await caches[0].claim("refresh:points", seconds=1)


async def test_refresh_uses_all_pages_and_keeps_both_locker_types(directories):
    _, caches, _ = directories
    client = AsyncMock(spec=NovaPoshtaClient)
    client.get_points_page.side_effect = [
        ([_point("branch", "Відділення", "", "1", "branch")], True),
        (
            [_point("locker", "Поштомат", "", "1", NOVA_POSHTA_LOCKER_TYPE_REF)],
            False,
        ),
    ]
    refresh = DeliveryDirectoryRefreshService(client, caches[0], NovaPoshtaConfig())
    assert await refresh.refresh_points() == 2
    service = DeliveryDirectoryService(client, caches[1], NovaPoshtaConfig())
    assert [item.ref for item in await service.search_points("city", "")] == ["branch"]
    assert [
        item.ref
        for item in await service.search_points(
            "city",
            "",
            type_ref=NOVA_POSHTA_LOCKER_TYPE_REF,
        )
    ] == ["locker"]
    client.search_points.assert_not_awaited()


async def test_snapshot_storage_is_bounded_and_leases_are_owner_checked(directories):
    redis, caches, namespace = directories
    for index in range(4):
        await caches[0].save(
            f"points:{index}",
            PointSnapshot.create([], ttl=60, stale=60),
            group="points",
            capacity=2,
        )
    keys = [key async for key in redis.scan_iter(match=f"{namespace}:points:*")]
    assert len(keys) == 2
    token = await caches[0].claim("test", seconds=30)
    assert token is not None
    await caches[1].release("test", "wrong-owner")
    assert await caches[1].claim("test", seconds=30) is None
    await caches[0].release("test", token)
    assert await caches[1].claim("test", seconds=30) is not None


async def test_short_lived_write_does_not_expire_the_storage_index_early(directories):
    redis, caches, namespace = directories
    await caches[0].save(
        "long",
        PointSnapshot.create([], ttl=300, stale=300),
        group="queries",
    )
    await caches[0].save(
        "short",
        PointSnapshot.create([], ttl=1, stale=1),
        group="queries",
    )
    assert await redis.ttl(f"{namespace}:index:queries") > 590


async def test_cancelled_loader_releases_its_lease(directories):
    _, caches, _ = directories
    entered = asyncio.Event()

    async def load():
        entered.set()
        await asyncio.Event().wait()

    pending = asyncio.create_task(
        caches[0].remember("query:cancel", CitySnapshot, load)
    )
    await entered.wait()
    pending.cancel()
    with pytest.raises(asyncio.CancelledError):
        await pending
    assert await caches[1].claim("lookup:query:cancel", seconds=1)


async def test_invalid_and_expired_snapshots_are_not_served(directories):
    redis, caches, namespace = directories
    await redis.set(f"{namespace}:cities", "invalid-json", ex=30)
    assert await caches[0].read("cities", CitySnapshot) is None
    expired = CitySnapshot(items=(), fresh_until=time() - 30, expires_at=time() - 5)
    await redis.set(f"{namespace}:cities", expired.model_dump_json(), ex=30)
    assert await caches[0].read("cities", CitySnapshot) is None


async def test_query_failure_uses_recent_snapshot(directories):
    _, caches, _ = directories
    old = CitySnapshot(
        items=(NovaPoshtaCity("city", "Київ", "м. Київ"),),
        fresh_until=time() - 1,
        expires_at=time() + 300,
    )
    await caches[0].save("query:city", old, group="queries")

    async def fail():
        raise ServiceUnavailableError("Provider offline")

    result = await caches[1].remember("query:city", CitySnapshot, fail)
    assert result.items[0].ref == "city"


async def test_empty_city_refresh_keeps_last_successful_directory(directories):
    _, caches, _ = directories
    await caches[0].save(
        "cities",
        CitySnapshot.create(
            [NovaPoshtaCity("old", "Київ", "м. Київ")],
            ttl=60,
            stale=60,
        ),
        group="cities",
        capacity=1,
    )
    client = AsyncMock(spec=NovaPoshtaClient)
    client.get_cities_page.return_value = ([], False)
    refresh = DeliveryDirectoryRefreshService(client, caches[0], NovaPoshtaConfig())
    with pytest.raises(ServiceUnavailableError):
        await refresh.refresh_cities(force=True)
    current = await caches[1].read("cities", CitySnapshot)
    assert current is not None and current.items[0].ref == "old"


async def test_periodic_refresh_only_loads_stale_directories(directories):
    _, caches, _ = directories
    await caches[0].save(
        "cities",
        CitySnapshot.create(
            [NovaPoshtaCity("city", "Київ", "м. Київ")],
            ttl=43200,
            stale=86400,
        ),
        group="cities",
        capacity=1,
    )
    client = AsyncMock(spec=NovaPoshtaClient)
    client.get_points_page.return_value = (
        [_point("p", "Point", "", "1", "branch")],
        False,
    )
    refresh = DeliveryDirectoryRefreshService(client, caches[0], NovaPoshtaConfig())
    await refresh.refresh_directories()
    await refresh.refresh_directories()
    client.get_cities_page.assert_not_awaited()
    client.get_points_page.assert_awaited_once_with(None, 1)


async def test_provider_gate_is_shared_bounded_and_honors_cooldown(directories):
    redis, _, _ = directories
    identity = uuid4().hex
    gates = [
        NovaPoshtaRequestGate(redis, identity, interval=0.05, max_wait=0.5)
        for _ in range(4)
    ]
    starts = []

    async def acquire(gate):
        await gate.acquire()
        starts.append(monotonic())

    try:
        await asyncio.gather(*(acquire(gate) for gate in gates))
        assert all(
            b - a >= 0.045
            for a, b in zip(sorted(starts), sorted(starts)[1:], strict=False)
        )
        await gates[0].block(2)
        started = monotonic()
        with pytest.raises(ServiceUnavailableError):
            await gates[1].acquire()
        assert monotonic() - started < 0.5
    finally:
        keys = [key async for key in redis.scan_iter(match=f"{gates[0]._prefix}:*")]
        if keys:
            await redis.delete(*keys)
