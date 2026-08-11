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
