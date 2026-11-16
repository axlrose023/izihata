import hashlib
import json
import logging
from collections.abc import Awaitable, Callable

from redis.exceptions import RedisError
from taskiq.exceptions import TaskiqError

from app.api.common.exceptions import ServiceUnavailableError
from app.api.modules.delivery.cache import DeliveryDirectoryCache, DirectorySnapshot
from app.api.modules.delivery.utils import CitySearchIndex, match_points
from app.clients.nova_poshta import (
    POINTS_PAGE_SIZE,
    NovaPoshtaCity,
    NovaPoshtaClient,
    NovaPoshtaPoint,
)
from app.settings import NovaPoshtaConfig

logger = logging.getLogger(__name__)
CitySnapshot = DirectorySnapshot[NovaPoshtaCity]
PointSnapshot = DirectorySnapshot[NovaPoshtaPoint]


class DeliveryDirectoryService:
    def __init__(
        self,
        client: NovaPoshtaClient,
        cache: DeliveryDirectoryCache,
        config: NovaPoshtaConfig,
        enqueue: Callable[[str, str], Awaitable[None]] | None = None,
    ):
        self._client = client
        self._cache = cache
        self._enabled = config.directory_enabled
        self._enqueue = enqueue
        self._city_source: CitySnapshot | None = None
        self._city_index = CitySearchIndex(())

    async def search_cities(self, search: str) -> list[NovaPoshtaCity]:
        if not self._enabled:
            return await self._client.search_cities(search)
        directory = await self._cache.read("cities", CitySnapshot)
        if directory:
            if self._city_source is not directory:
                self._city_index = CitySearchIndex(directory.items)
                self._city_source = directory
            matches = self._city_index.search(search)
            if matches:
                return matches
        key = self._query_key("cities", " ".join(search.casefold().split()))

        async def load() -> CitySnapshot:
            return CitySnapshot.create(
                await self._client.search_cities(search), ttl=300, stale=900
            )

        return list((await self._cache.remember(key, CitySnapshot, load)).items)

    async def search_points(
        self,
        city_ref: str,
        search: str,
        type_ref: str | None = None,
        page: int = 1,
    ) -> list[NovaPoshtaPoint]:
        if not self._enabled:
            return await self._client.search_points(
                city_ref, search, type_ref=type_ref, page=page
            )
        directory = await self._cache.read(f"points:{city_ref}", PointSnapshot)
        await self._cache.touch_city(city_ref)
        if directory is None or not directory.is_fresh:
            await self._schedule_refresh(city_ref)
        if directory:
            return match_points(
                directory.items, search, type_ref, page, POINTS_PAGE_SIZE
            )
        key = self._query_key(
            "points", city_ref, " ".join(search.casefold().split()), type_ref, page
        )

        async def load() -> PointSnapshot:
            return PointSnapshot.create(
                await self._client.search_points(
                    city_ref, search, type_ref=type_ref, page=page
                ),
                ttl=300,
                stale=900,
            )

        return list((await self._cache.remember(key, PointSnapshot, load)).items)

    async def _schedule_refresh(self, city_ref: str) -> None:
        if self._enqueue is None:
            return
        key = f"dispatch:{city_ref}"
        token = await self._cache.claim(key, seconds=300)
        if token is None:
            return
        try:
            await self._enqueue(city_ref, token)
        except (TaskiqError, RedisError, ServiceUnavailableError):
            await self._cache.release(key, token)
            logger.warning("Delivery directory refresh could not be queued")

    @staticmethod
    def _query_key(*parts: object) -> str:
        digest = hashlib.sha256(json.dumps(parts).encode()).hexdigest()
        return f"query:{digest}"
