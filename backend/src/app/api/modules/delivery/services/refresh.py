"""Publish complete directory snapshots under one cross-worker lease."""

import asyncio
import logging
from collections.abc import Awaitable, Callable

from app.api.common.exceptions import ServiceUnavailableError
from app.api.modules.delivery.cache import DeliveryDirectoryCache, DirectorySnapshot
from app.api.modules.delivery.services.directory import CitySnapshot, PointSnapshot
from app.clients.nova_poshta import NovaPoshtaCity, NovaPoshtaClient, NovaPoshtaPoint
from app.clients.nova_poshta_gate import directory_unavailable
from app.settings import NovaPoshtaConfig

logger = logging.getLogger(__name__)


class DeliveryDirectoryRefreshService:
    def __init__(
        self,
        client: NovaPoshtaClient,
        cache: DeliveryDirectoryCache,
        config: NovaPoshtaConfig,
    ):
        self._client = client
        self._cache = cache
        self._config = config

    async def refresh_directories(self) -> None:
        token = await self._cache.claim("refresh:batch", seconds=900)
        if not token:
            return
        try:
            async with asyncio.timeout(600):
                await self._refresh(
                    "cities", CitySnapshot, self._client.get_cities_page, ttl=12 * 3600
                )
                await self._refresh(
                    "points",
                    PointSnapshot,
                    self._client.get_points_page,
                    ttl=self._config.directory_ttl_seconds,
                )
        except (ServiceUnavailableError, TimeoutError):
            logger.warning(
                "Delivery directory refresh interrupted; keeping last snapshot"
            )
        finally:
            await self._cache.release("refresh:batch", token)

    async def _refresh[T: (NovaPoshtaCity, NovaPoshtaPoint)](
        self,
        key: str,
        model: type[DirectorySnapshot[T]],
        fetch: Callable[[int], Awaitable[tuple[list[T], bool]]],
        *,
        ttl: int,
    ) -> None:
        current = await self._cache.read(key, model, refresh=True)
        if current and current.is_fresh:
            return
        rows: dict[str, T] = {}
        for page in range(1, 1001):
            items, more = await fetch(page)
            previous = len(rows)
            rows.update((item.ref, item) for item in items)
            if not more:
                break
            if len(rows) == previous:
                raise directory_unavailable()
        else:
            raise directory_unavailable()
        if not rows:
            raise directory_unavailable()
        await self._cache.save(
            key,
            model.create(
                list(rows.values()), ttl=ttl, stale=self._config.directory_stale_seconds
            ),
        )
        logger.info(
            "Nova Poshta directory refreshed",
            extra={"directory": key, "count": len(rows)},
        )
