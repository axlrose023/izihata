import app.settings
from app.settings import (
    APIConfig,
    Config,
    JwtConfig,
    PostgresConfig,
    RateLimitConfig,
    RedisConfig,
)

_test_config = Config(
    env="local",
    database_url_override="sqlite+aiosqlite:///file::memory:?cache=shared&uri=true",
    api=APIConfig(allowed_origins=["*"], allowed_hosts=["*"]),
    jwt=JwtConfig(secret_key="test-secret-key-for-testing-only"),
    postgres=PostgresConfig(user="test", password="test", host="localhost", db="test"),
    redis=RedisConfig(host="localhost"),
    rate_limit=RateLimitConfig(enabled=False),
)

app.settings.get_config = lambda: _test_config

pytest_plugins = [
    "tests.fixtures.catalog",
    "tests.fixtures.core.app",
    "tests.fixtures.core.session",
    "tests.fixtures.orders",
    "tests.fixtures.users.admin",
    "tests.fixtures.auth",
]
