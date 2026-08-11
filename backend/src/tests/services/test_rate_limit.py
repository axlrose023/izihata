from types import SimpleNamespace
from typing import Any, cast

import pytest

from app.api.common.exceptions import ServiceUnavailableError, TooManyRequestsError
from app.services.rate_limit import RateLimitPolicy, RateLimitService
from app.settings import Config


class FakeRedis:
    def __init__(self, result: list[int] | None = None, error: Exception | None = None):
        self.result = result or [1, 60]
        self.error = error

    async def eval(self, *args: object) -> list[int]:
        if self.error:
            raise self.error
        return self.result


def config_with_rate_limit(enabled: bool, *, fail_open: bool = False) -> Config:
    return cast(
        Config,
        SimpleNamespace(
            rate_limit=SimpleNamespace(enabled=enabled, fail_open=fail_open)
        ),
    )


@pytest.mark.asyncio
async def test_rejects_request_over_fixed_window_limit():
    redis = cast(Any, FakeRedis([6, 42]))
    service = RateLimitService(redis, config_with_rate_limit(True))

    with pytest.raises(TooManyRequestsError) as error:
        await service.check("client", RateLimitPolicy("login", 5, 60))

    assert error.value.headers == {"Retry-After": "42"}


@pytest.mark.asyncio
async def test_allows_request_when_limiter_is_disabled_or_configured_fail_open():
    disabled = RateLimitService(
        cast(Any, FakeRedis([99, 60])),
        config_with_rate_limit(False),
    )
    unavailable = RateLimitService(
        cast(Any, FakeRedis(error=ConnectionError("offline"))),
        config_with_rate_limit(True, fail_open=True),
    )

    await disabled.check("client", RateLimitPolicy("lead", 1, 60))
    await unavailable.check("client", RateLimitPolicy("lead", 1, 60))


@pytest.mark.asyncio
async def test_rejects_request_when_limiter_is_unavailable():
    service = RateLimitService(
        cast(Any, FakeRedis(error=ConnectionError("offline"))),
        config_with_rate_limit(True),
    )

    with pytest.raises(ServiceUnavailableError):
        await service.check("client", RateLimitPolicy("login", 5, 60))
