import uuid

import pytest
from redis.asyncio import Redis

from app.api.common.exceptions import TooManyRequestsError
from app.services.rate_limit import RateLimitPolicy, RateLimitService
from app.settings import get_config

pytestmark = pytest.mark.integration


@pytest.mark.asyncio(loop_scope="session")
async def test_redis_rate_limit_is_atomic_and_returns_retry_after():
    config = get_config()
    redis = Redis.from_url(config.redis_url, decode_responses=True)
    policy = RateLimitPolicy(f"integration-{uuid.uuid4()}", 2, 60)
    service = RateLimitService(redis, config)
    identity = str(uuid.uuid4())

    try:
        await service.check(identity, policy)
        await service.check(identity, policy)
        with pytest.raises(TooManyRequestsError) as error:
            await service.check(identity, policy)
        assert error.value.headers is not None
        assert int(error.value.headers["Retry-After"]) > 0
    finally:
        await redis.delete(f"izihata:rate-limit:{policy.scope}:{identity}")
        await redis.aclose()


@pytest.mark.asyncio(loop_scope="session")
async def test_staff_login_endpoint_throttles_repeated_attempts():
    """The limiter has to be wired to the route, not just exist as a service.

    The unit suite runs with rate limiting disabled, so this is the only place
    the guard on /auth/login is actually exercised.
    """
    from httpx import ASGITransport, AsyncClient

    from app.api.common.rate_limit import STAFF_LOGIN_RATE_LIMIT
    from app.application import get_production_app

    config = get_config()
    redis = Redis.from_url(config.redis_url, decode_responses=True)
    # The limiter keys on the client address, and TrustedHostMiddleware only
    # accepts the configured hosts — both have to be set explicitly here.
    client_host = "127.0.0.1"
    key = f"izihata:rate-limit:{STAFF_LOGIN_RATE_LIMIT.scope}:{client_host}"
    await redis.delete(key)

    payload = {"username": f"missing-{uuid.uuid4().hex[:8]}", "password": "wrong-pass"}
    statuses: list[int] = []
    try:
        async with AsyncClient(
            transport=ASGITransport(
                app=get_production_app(), client=(client_host, 5000)
            ),
            base_url="http://localhost",
        ) as client:
            for _ in range(STAFF_LOGIN_RATE_LIMIT.requests + 1):
                response = await client.post("/api/v1/auth/login", json=payload)
                statuses.append(response.status_code)
    finally:
        await redis.delete(key)
        await redis.aclose()

    allowed = statuses[: STAFF_LOGIN_RATE_LIMIT.requests]
    assert allowed == [401] * STAFF_LOGIN_RATE_LIMIT.requests, statuses
    assert statuses[-1] == 429, statuses
