from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from app.ioc import AppProvider
from app.settings import RedisConfig, get_config


@pytest.mark.asyncio
async def test_http_redis_has_bounded_network_wait():
    fake = AsyncMock()
    pool = object()
    with (
        patch("app.ioc.BlockingConnectionPool.from_url", return_value=pool) as create,
        patch("app.ioc.Redis.from_pool", return_value=fake) as client,
    ):
        resource = AppProvider().get_redis(get_config())
        assert await anext(resource) is fake
        create.assert_called_once_with(
            get_config().redis_url,
            max_connections=64,
            timeout=2,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        client.assert_called_once_with(pool)
        await resource.aclose()
        fake.aclose.assert_awaited_once()


@pytest.mark.parametrize("value", [0, -1, 11])
def test_timeout_bounds(value):
    with pytest.raises(ValidationError):
        RedisConfig(host="localhost", socket_timeout_seconds=value)


@pytest.mark.parametrize("field", ["max_connections", "pool_timeout_seconds"])
@pytest.mark.parametrize("value", [0, -1, 1000])
def test_pool_bounds(field, value):
    with pytest.raises(ValidationError):
        RedisConfig(host="localhost", **{field: value})
