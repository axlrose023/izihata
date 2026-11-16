"""Delivery/Redis burst benchmark. Uses synthetic directories, never the NP API.

Run with the backend's Python environment. Only the unique benchmark Redis
namespace is written; it is deleted afterwards and expires automatically.
"""

import argparse
import asyncio
import json
from time import perf_counter
from unittest.mock import AsyncMock
from uuid import uuid4

from redis.asyncio import Redis

from app.api.modules.delivery.cache import DeliveryDirectoryCache
from app.api.modules.delivery.services.directory import (
    CitySnapshot,
    DeliveryDirectoryService,
    PointSnapshot,
)
from app.clients.nova_poshta import NovaPoshtaCity, NovaPoshtaClient, NovaPoshtaPoint
from app.settings import NovaPoshtaConfig, get_config


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(f"Delivery benchmark failed: {message}")


async def benchmark(concurrency: int, size: int) -> None:
    namespace = f"izihata:delivery-benchmark:{uuid4().hex}"
    connections = [
        Redis.from_url(get_config().redis_url, decode_responses=True) for _ in range(4)
    ]
    caches = [
        DeliveryDirectoryCache(redis, namespace=namespace) for redis in connections
    ]
    provider = AsyncMock(spec=NovaPoshtaClient)
    services = [
        DeliveryDirectoryService(provider, cache, NovaPoshtaConfig())
        for cache in caches
    ]
    reports = []

    async def measure(name, operation):
        durations = []
        before = provider.search_points.await_count + provider.search_cities.await_count

        async def request(index):
            started = perf_counter()
            await operation(services[index % 4], index)
            durations.append((perf_counter() - started) * 1000)

        started = perf_counter()
        await asyncio.gather(*(request(index) for index in range(concurrency)))
        ordered = sorted(durations)
        reports.append(
            {
                "scenario": name,
                "requests": concurrency,
                "elapsed_ms": round((perf_counter() - started) * 1000, 2),
                "p50_ms": round(ordered[len(ordered) // 2], 2),
                "p95_ms": round(ordered[int((len(ordered) - 1) * 0.95)], 2),
                "provider_calls": (
                    provider.search_points.await_count
                    + provider.search_cities.await_count
                    - before
                ),
            }
        )

    try:

        async def cold_provider(*args, **kwargs):
            await asyncio.sleep(0.02)
            return [NovaPoshtaPoint("cold", "Відділення №1", "", "1", "branch")]

        provider.search_points.side_effect = cold_provider

        async def cold(service, index):
            result = await service.search_points("cold", "1")
            require(result[0].ref == "cold", "unexpected cold lookup result")

        await measure("cold identical lookup, shared single flight", cold)
        require(
            provider.search_points.await_count == 1, "duplicate cold provider calls"
        )
        await caches[0].save(
            "points:city",
            PointSnapshot.create(
                [
                    NovaPoshtaPoint(
                        str(index),
                        f"Відділення №{index}",
                        f"вул. Тестова, {index}",
                        str(index),
                        "branch",
                    )
                    for index in range(1, size + 1)
                ],
                ttl=60,
                stale=60,
            ),
            group="points",
        )
        await caches[0].save(
            "cities",
            CitySnapshot.create(
                [
                    NovaPoshtaCity(
                        str(index), f"Місто {index}", f"Місто {index}, область"
                    )
                    for index in range(size)
                ],
                ttl=60,
                stale=60,
            ),
            group="cities",
            capacity=1,
        )

        async def points(service, index):
            number = str(index % size + 1)
            result = await service.search_points("city", number)
            require(len(result) == 1 and result[0].number == number, "wrong point")

        async def cities(service, index):
            name = f"Місто {index % 100}"
            result = await service.search_cities(name)
            require(result[0].name == name, "wrong city")

        await measure("different point numbers in a cached city", points)
        await measure("cities from the cached country directory", cities)
        require(
            all(report["provider_calls"] == 0 for report in reports[1:]),
            "warm lookup called the provider",
        )
        print(
            json.dumps(
                {
                    "instances": 4,
                    "directory_size": size,
                    "real_nova_poshta_calls": 0,
                    "results": reports,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    finally:
        keys = [key async for key in connections[0].scan_iter(match=f"{namespace}:*")]
        if keys:
            await connections[0].delete(*keys)
        await asyncio.gather(*(redis.aclose() for redis in connections))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--concurrency", type=int, default=500, choices=range(1, 2001))
    parser.add_argument("--size", type=int, default=10000, choices=range(100, 20001))
    arguments = parser.parse_args()
    asyncio.run(benchmark(arguments.concurrency, arguments.size))
