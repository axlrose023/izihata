"""Short-lived public catalog metadata cache; never caches prices or orders."""

import asyncio
import hashlib
import json
import logging
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any
from weakref import WeakValueDictionary

from pydantic import TypeAdapter, ValidationError
from redis.asyncio import Redis
from redis.exceptions import RedisError

if TYPE_CHECKING:
    from app.database.uow import UnitOfWork
logger = logging.getLogger(__name__)


class PublicCatalogCache:
    namespace = "public-catalog:v1"

    def __init__(self, redis: Redis, *, enabled: bool = True, ttl: int = 30):
        self._redis = redis
        self._enabled = enabled
        self._ttl = ttl
        self._locks: WeakValueDictionary[str, asyncio.Lock] = WeakValueDictionary()

    async def remember[T](
        self, key: str, response_type: Any, load: Callable[[], Awaitable[T]]
    ) -> T:
        if not self._enabled:
            return await load()
        adapter = TypeAdapter(response_type)
        try:
            generation = await self._redis.get(f"{self.namespace}:generation") or "0"
            full_key = f"{self.namespace}:{generation}:{hashlib.sha256(key.encode()).hexdigest()}"
            lock = self._locks.setdefault(full_key, asyncio.Lock())
            async with lock:
                cached = await self._redis.get(full_key)
                if cached is not None:
                    try:
                        return adapter.validate_json(cached)
                    except (ValidationError, ValueError):
                        pass
                value = await load()
                try:
                    await self._redis.set(
                        full_key, adapter.dump_json(value), ex=self._ttl
                    )
                except RedisError:
                    logger.warning("Public catalog cache write unavailable")
                return value
        except RedisError:
            logger.warning("Public catalog cache unavailable; reading database")
            return await load()

    async def invalidate(self) -> None:
        if self._enabled:
            try:
                await self._redis.incr(f"{self.namespace}:generation")
            except RedisError:
                logger.warning(
                    "Catalog cache invalidation unavailable; TTL will expire"
                )


def catalog_cache_key(resource: str, params: Any = None, **options: Any) -> str:
    filters = (
        params.model_dump(mode="json", exclude={"page", "page_size", "include_facets"})
        if params is not None
        else {}
    )
    # Spec-facet pages have their own output pagination.
    if resource == "spec-facets" and params is not None:
        filters.update(page=params.page, page_size=params.page_size)
    return json.dumps([resource, filters, options], sort_keys=True, ensure_ascii=False)


async def load_cached[T](
    cache: PublicCatalogCache | None,
    key: str,
    response_type: Any,
    load: Callable[[], Awaitable[T]],
) -> T:
    return await cache.remember(key, response_type, load) if cache else await load()


async def commit_catalog(uow: "UnitOfWork", cache: PublicCatalogCache | None) -> None:
    await uow.commit()
    if cache:
        await cache.invalidate()
