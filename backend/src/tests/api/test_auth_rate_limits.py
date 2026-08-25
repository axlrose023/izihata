from app.api.common.rate_limit import (
    CUSTOMER_LOGIN_RATE_LIMIT,
    CUSTOMER_REFRESH_RATE_LIMIT,
    STAFF_LOGIN_RATE_LIMIT,
    STAFF_REFRESH_RATE_LIMIT,
)


def test_staff_and_customer_auth_limits_use_isolated_scopes() -> None:
    policies = (
        STAFF_LOGIN_RATE_LIMIT,
        STAFF_REFRESH_RATE_LIMIT,
        CUSTOMER_LOGIN_RATE_LIMIT,
        CUSTOMER_REFRESH_RATE_LIMIT,
    )

    assert len({policy.scope for policy in policies}) == len(policies)
    assert STAFF_LOGIN_RATE_LIMIT.requests == CUSTOMER_LOGIN_RATE_LIMIT.requests == 5
    assert (
        STAFF_REFRESH_RATE_LIMIT.requests == CUSTOMER_REFRESH_RATE_LIMIT.requests == 20
    )
