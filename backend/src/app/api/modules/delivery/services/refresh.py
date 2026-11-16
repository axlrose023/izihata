"""Build complete replacement snapshots; never publish partial directory pages."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from functools import partial

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

    async def refresh_cities(self, *, force: bool = False) -> int:
        return await self._refresh(
            "cities",
            CitySnapshot,
            self._client.get_cities_page,
            ttl=12 * 3600,
            max_pages=200,
            force=force,
        )

    async def refresh_points(self, *, force: bool = False) -> int:
        return await self._refresh(
            "points",
            PointSnapshot,
            partial(self._client.get_points_page, None),
            ttl=self._config.directory_ttl_seconds,
            max_pages=1000,
            force=force,
        )

    async def _refresh[T: (NovaPoshtaCity, NovaPoshtaPoint)](
        self,
        key: str,
        model: type[DirectorySnapshot[T]],
        fetch: Callable[[int], Awaitable[tuple[list[T], bool]]],
        *,
        ttl: int,
        max_pages: int,
        force: bool,
    ) -> int:
        current = await self._cache.read(key, model, refresh=True)
        if current and current.is_fresh and not force:
            return len(current.items)
        token = await self._cache.claim(f"refresh:{key}", seconds=900)
        if not token:
            return 0
        try:
            # A different loader may finish between the initial read and lease.
            current = await self._cache.read(key, model, refresh=True)
            if current and current.is_fresh and not force:
                return len(current.items)
            rows: dict[str, T] = {}
            async with asyncio.timeout(600):
                for page in range(1, max_pages + 1):
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
                    list(rows.values()),
                    ttl=ttl,
                    stale=self._config.directory_stale_seconds,
                ),
                group=key,
                capacity=1,
            )
            logger.info(
                "Nova Poshta directory refreshed",
                extra={"directory": key, "count": len(rows)},
            )
            return len(rows)
        except TimeoutError as exc:
            raise directory_unavailable() from exc
        finally:
            await self._cache.release(f"refresh:{key}", token)

    async def refresh_directories(self) -> None:
        token = await self._cache.claim("refresh:batch", seconds=900)
        if not token:
            return
        try:
            async with asyncio.timeout(600):
                await self.refresh_cities()
                await self.refresh_points()
        except (ServiceUnavailableError, TimeoutError):
            logger.warning(
                "Delivery directory refresh interrupted; keeping last snapshot"
            )
        finally:
            await self._cache.release("refresh:batch", token)
