from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from app.ioc import AppProvider
from app.settings import RedisConfig, get_config


@pytest.mark.asyncio
async def test_http_redis_has_bounded_network_wait():
    fake = AsyncMock()
    with patch("app.ioc.Redis.from_url", return_value=fake) as create:
        resource = AppProvider().get_redis(get_config())
        assert await anext(resource) is fake
        create.assert_called_once_with(
            get_config().redis_url,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        await resource.aclose()
        fake.aclose.assert_awaited_once()


@pytest.mark.parametrize("value", [0, -1, 11])
def test_timeout_bounds(value):
    with pytest.raises(ValidationError):
        RedisConfig(host="localhost", socket_timeout_seconds=value)
