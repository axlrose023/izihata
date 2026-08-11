import pytest
from pydantic import ValidationError

from app.settings import (
    APIConfig,
    Config,
    JwtConfig,
    OutboxConfig,
    PostgresConfig,
    RedisConfig,
)


def config_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "env": "local",
        "api": APIConfig(),
        "jwt": JwtConfig(secret_key="a" * 32),
        "postgres": PostgresConfig(
            user="postgres",
            password="postgres",
            host="localhost",
            db="izihata",
        ),
        "redis": RedisConfig(host="localhost"),
    }
    payload.update(overrides)
    return payload


def test_rejects_non_hs256_jwt_algorithm():
    with pytest.raises(ValidationError):
        JwtConfig.model_validate({"secret_key": "a" * 32, "algorithm": "HS512"})


def test_rejects_weak_production_secret():
    with pytest.raises(ValidationError):
        Config.model_validate(
            config_payload(env="prod", jwt=JwtConfig(secret_key="too-short"))
        )


def test_rejects_unknown_business_timezone():
    with pytest.raises(ValidationError):
        Config.model_validate(config_payload(business_timezone="Invalid/Timezone"))


def test_rejects_wildcard_http_trust_in_production():
    with pytest.raises(ValidationError):
        Config.model_validate(
            config_payload(
                env="prod",
                api=APIConfig(allowed_origins=["*"], allowed_hosts=["*"]),
            )
        )


def test_rejects_page_default_larger_than_maximum():
    with pytest.raises(ValidationError):
        APIConfig(page_default_size=101, page_max_size=100)


def test_rejects_refresh_lifetime_shorter_than_access():
    with pytest.raises(ValidationError):
        JwtConfig(
            secret_key="a" * 32,
            access_token_expires_in_minutes=60,
            refresh_expires_in_minutes=30,
        )


def test_rejects_outbox_lease_shorter_than_maximum_batch_runtime():
    with pytest.raises(ValidationError):
        OutboxConfig(
            batch_size=10,
            dispatch_timeout_seconds=15,
            lease_seconds=150,
        )
