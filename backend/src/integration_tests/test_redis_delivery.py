import asyncio
import json
import threading
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


def _client():
    client = AsyncMock(spec=NovaPoshtaClient)
    client.get_cities_page.return_value = (
        [NovaPoshtaCity("city", "Київ", "м. Київ")],
        False,
    )
    return client


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


@pytest.mark.parametrize("kind", ["cities", "points"])
async def test_cold_index_build_yields_to_io_and_runs_once(
    directories, monkeypatch, kind
):
    import app.api.modules.delivery.services.directory as directory_module

    _, caches, _ = directories
    city = NovaPoshtaCity("city", "Київ", "м. Київ")
    point = _point("p", "Відділення №1", "", "1", "branch")
    snapshot = (
        CitySnapshot.create([city], ttl=60, stale=60)
        if kind == "cities"
        else PointSnapshot.create([point], ttl=60, stale=60)
    )
    await caches[0].save(kind, snapshot)
    client = _client()
    service = DeliveryDirectoryService(client, caches[0], NovaPoshtaConfig())
    index_name = "CitySearchIndex" if kind == "cities" else "PointSearchIndex"
    index_factory = getattr(directory_module, index_name)
    loop = asyncio.get_running_loop()
    builds = 0

    def build(items):
        nonlocal builds
        builds += 1
        io_processed = threading.Event()
        loop.call_soon_threadsafe(io_processed.set)
        assert io_processed.wait(1), "Index construction blocked the request loop"
        return index_factory(items)

    monkeypatch.setattr(directory_module, index_name, build)
    results = await asyncio.gather(
        *(
            service.search_cities("Київ")
            if kind == "cities"
            else service.search_points("city", "1")
            for _ in range(100)
        )
    )
    assert all(len(result) == 1 for result in results)
    assert builds == 1
    client.search_cities.assert_not_awaited()
    client.search_points.assert_not_awaited()


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
    )
    client = _client()
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
    )
    client = _client()
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
    )
    enqueue = AsyncMock()
    services = [
        DeliveryDirectoryService(_client(), cache, NovaPoshtaConfig(), enqueue)
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
        ttl=-1,
        stale=86400,
    )
    await caches[0].save("points", original)
    client = _client()
    client.get_points_page.side_effect = [
        ([_point("new", "Нове відділення", "", "2", "branch")], True),
        ServiceUnavailableError("Provider down"),
    ]
    refresh = DeliveryDirectoryRefreshService(client, caches[0], NovaPoshtaConfig())
    await refresh.refresh_directories()
    snapshot = await caches[1].read("points", PointSnapshot)
    assert snapshot is not None and snapshot.items[0].ref == "old"
    assert await caches[0].claim("refresh:batch", seconds=1)


async def test_failed_background_refresh_is_not_requeued_on_each_stale_read(
    directories,
):
    redis, caches, namespace = directories
    await caches[0].save(
        "cities",
        CitySnapshot.create(
            [NovaPoshtaCity("city", "Київ", "м. Київ")], ttl=60, stale=60
        ),
    )
    await caches[0].save(
        "points",
        PointSnapshot(
            items=(_point("p", "Point", "", "1", "branch"),),
            fresh_until=time() - 1,
            expires_at=time() + 300,
        ),
    )
    provider = _client()
    provider.get_points_page.side_effect = ServiceUnavailableError("Provider offline")
    refresh = DeliveryDirectoryRefreshService(provider, caches[0], NovaPoshtaConfig())
    enqueue = AsyncMock(side_effect=refresh.refresh_directories)
    service = DeliveryDirectoryService(provider, caches[1], NovaPoshtaConfig(), enqueue)
    for _ in range(20):
        assert (await service.search_points("city", "1"))[0].ref == "p"
    enqueue.assert_awaited_once_with()
    provider.get_points_page.assert_awaited_once_with(1)
    assert await redis.ttl(f"{namespace}:lock:dispatch") > 240


async def test_refresh_uses_all_pages_and_keeps_both_locker_types(directories):
    _, caches, _ = directories
    client = _client()
    client.get_points_page.side_effect = [
        ([_point("branch", "Відділення", "", "1", "branch")], True),
        (
            [_point("locker", "Поштомат", "", "1", NOVA_POSHTA_LOCKER_TYPE_REF)],
            False,
        ),
    ]
    refresh = DeliveryDirectoryRefreshService(client, caches[0], NovaPoshtaConfig())
    await refresh.refresh_directories()
    assert len((await caches[1].read("points", PointSnapshot)).items) == 2
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
    for index in range(513):
        await caches[0].save(
            f"query:{index}",
            PointSnapshot.create([], ttl=60, stale=60),
        )
    keys = [key async for key in redis.scan_iter(match=f"{namespace}:query:*")]
    assert len(keys) == 512
    token = await caches[0].claim("test", seconds=30)
    assert token is not None
    await caches[1].release("test", "wrong-owner")
    assert await caches[1].claim("test", seconds=30) is None
    await caches[0].release("test", token)
    assert await caches[1].claim("test", seconds=30) is not None


async def test_short_lived_write_does_not_expire_the_storage_index_early(directories):
    redis, caches, namespace = directories
    await caches[0].save(
        "query:long",
        PointSnapshot.create([], ttl=300, stale=300),
    )
    await caches[0].save(
        "query:short",
        PointSnapshot.create([], ttl=1, stale=1),
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
    await caches[0].save("query:city", old)

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
            ttl=-1,
            stale=60,
        ),
    )
    client = _client()
    client.get_cities_page.return_value = ([], False)
    refresh = DeliveryDirectoryRefreshService(client, caches[0], NovaPoshtaConfig())
    await refresh.refresh_directories()
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
    )
    client = _client()
    client.get_points_page.return_value = (
        [_point("p", "Point", "", "1", "branch")],
        False,
    )
    refresh = DeliveryDirectoryRefreshService(client, caches[0], NovaPoshtaConfig())
    await refresh.refresh_directories()
    await refresh.refresh_directories()
    client.get_cities_page.assert_not_awaited()
    client.get_points_page.assert_awaited_once_with(1)


@pytest.mark.parametrize("kind", ["cities", "points"])
async def test_unchanged_snapshot_reuses_index_and_new_snapshot_replaces_it(
    directories, monkeypatch, kind
):
    import app.api.modules.delivery.services.directory as module

    _, caches, _ = directories
    model = CitySnapshot if kind == "cities" else PointSnapshot
    item = (
        NovaPoshtaCity("city", "Київ", "м. Київ")
        if kind == "cities"
        else _point("p", "Point", "", "1", "branch")
    )
    snapshot = model.create([item], ttl=60, stale=60)
    await caches[0].save(kind, snapshot)
    service = DeliveryDirectoryService(_client(), caches[1], NovaPoshtaConfig())
    index_name = "CitySearchIndex" if kind == "cities" else "PointSearchIndex"
    factory = getattr(module, index_name)
    builds = []

    def build(items):
        builds.append(items)
        return factory(items)

    monkeypatch.setattr(module, index_name, build)

    async def search():
        return (
            await service.search_cities("Київ")
            if kind == "cities"
            else await service.search_points("city", "1")
        )

    await search()
    original = await caches[1].read(kind, model)
    for _ in range(3):
        assert await caches[1].read(kind, model, refresh=True) is original
        await search()
    assert len(builds) == 1
    caches[1]._local.clear()
    await search()
    assert len(builds) == 1
    replacement = model.create([item], ttl=120, stale=60)
    await caches[0].save(kind, replacement)
    assert (
        await caches[1].read(kind, model, refresh=True)
    ).version == replacement.version
    await search()
    assert len(builds) == 2


async def test_background_refresh_has_one_owner_across_workers(directories):
    _, caches, _ = directories
    client = _client()

    async def points(page):
        await asyncio.sleep(0.02)
        return [_point("p", "Point", "", "1", "branch")], False

    client.get_points_page.side_effect = points
    workers = [
        DeliveryDirectoryRefreshService(client, cache, NovaPoshtaConfig())
        for cache in caches
    ]
    await asyncio.gather(*(worker.refresh_directories() for worker in workers))
    client.get_cities_page.assert_awaited_once_with(1)
    client.get_points_page.assert_awaited_once_with(1)
    assert await caches[0].claim("refresh:batch", seconds=1)


async def test_non_progressing_refresh_keeps_previous_snapshot(directories):
    _, caches, _ = directories
    original = PointSnapshot.create(
        [_point("old", "Old", "", "1", "branch")], ttl=-1, stale=60
    )
    await caches[0].save("points", original)
    client = _client()
    client.get_points_page.return_value = (
        [_point("new", "New", "", "2", "branch")],
        True,
    )
    await DeliveryDirectoryRefreshService(
        client, caches[0], NovaPoshtaConfig()
    ).refresh_directories()
    assert (await caches[1].read("points", PointSnapshot)).items == original.items
    assert client.get_points_page.await_count == 2


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
