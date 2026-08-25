from fastapi import Request

from app.services.rate_limit import RateLimitPolicy, RateLimitService

STAFF_LOGIN_RATE_LIMIT = RateLimitPolicy("staff-auth-login", 5, 60)
STAFF_REFRESH_RATE_LIMIT = RateLimitPolicy("staff-auth-refresh", 20, 60)
CUSTOMER_LOGIN_RATE_LIMIT = RateLimitPolicy("customer-auth-login", 5, 60)
CUSTOMER_REFRESH_RATE_LIMIT = RateLimitPolicy("customer-auth-refresh", 20, 60)
QUOTE_RATE_LIMIT = RateLimitPolicy("checkout-quote", 30, 60)
ORDER_RATE_LIMIT = RateLimitPolicy("order-create", 10, 60)
LEAD_RATE_LIMIT = RateLimitPolicy("lead-create", 10, 60)


class RateLimit:
    def __init__(self, policy: RateLimitPolicy):
        self._policy = policy

    async def __call__(self, request: Request) -> None:
        container = request.state.dishka_container
        service: RateLimitService = await container.get(RateLimitService)
        identity = request.client.host if request.client else "unknown"
        await service.check(identity, self._policy)
