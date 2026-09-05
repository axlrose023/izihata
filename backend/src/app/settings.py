from functools import lru_cache
from pathlib import Path
from typing import ClassVar, Literal, final
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from yarl import URL


class PostgresConfig(BaseModel):
    user: str
    password: str
    host: str
    port: int = Field(default=5432, ge=1, le=65535)
    db: str
    pool_size: int = Field(default=10, ge=1, le=100)
    max_overflow: int = Field(default=20, ge=0, le=100)
    pool_timeout_seconds: int = Field(default=30, ge=1, le=300)
    pool_recycle_seconds: int = Field(default=1800, ge=60, le=86400)
    statement_timeout_ms: int = Field(default=15000, ge=1000, le=300000)


class RedisConfig(BaseModel):
    host: str
    port: int = Field(default=6379, ge=1, le=65535)
    db: int = Field(default=0, ge=0)


class RateLimitConfig(BaseModel):
    enabled: bool = True
    fail_open: bool = False


class NovaPoshtaConfig(BaseModel):
    api_url: str = "https://api.novaposhta.ua/v2.0/json/"
    api_key: SecretStr | None = None
    timeout_seconds: float = Field(default=5, gt=0, le=30)


class OutboxConfig(BaseModel):
    batch_size: int = Field(default=10, ge=1, le=100)
    lease_seconds: int = Field(default=300, ge=30, le=3600)
    dispatch_timeout_seconds: float = Field(default=15, gt=0, le=120)
    max_attempts: int = Field(default=8, ge=1, le=20)
    retention_days: int = Field(default=30, ge=1, le=365)

    @model_validator(mode="after")
    def validate_processing_lease(self) -> "OutboxConfig":
        maximum_batch_runtime = self.batch_size * self.dispatch_timeout_seconds
        if self.lease_seconds <= maximum_batch_runtime:
            raise ValueError(
                "outbox lease_seconds must exceed the maximum batch dispatch time"
            )
        return self


class JwtConfig(BaseModel):
    secret_key: str
    algorithm: Literal["HS256"] = "HS256"
    access_token_expires_in_minutes: int = Field(default=30, ge=1, le=1440)
    refresh_expires_in_minutes: int = Field(default=1440, ge=1, le=525600)

    @model_validator(mode="after")
    def validate_token_lifetimes(self) -> "JwtConfig":
        if self.refresh_expires_in_minutes < self.access_token_expires_in_minutes:
            raise ValueError("refresh token lifetime cannot be shorter than access")
        return self


class APIConfig(BaseModel):
    title: str = "IziHata API"
    version: str = "1.0.0"
    prefix: str = "/api/v1"
    port: int = Field(default=8000, ge=1, le=65535)
    host: str = "0.0.0.0"
    allowed_origins: list[str] = ["http://localhost:3000"]
    allowed_hosts: list[str] = ["localhost", "127.0.0.1"]
    forwarded_allow_ips: list[str] = ["127.0.0.1"]

    page_max_size: int = Field(default=100, ge=1, le=500)
    page_default_size: int = Field(default=10, ge=1, le=500)

    @model_validator(mode="after")
    def validate_page_sizes(self) -> "APIConfig":
        if self.page_default_size > self.page_max_size:
            raise ValueError("page_default_size cannot exceed page_max_size")
        return self


class PathsConfig:
    src_path = Path(__file__).parent.parent
    app_path = src_path / "app"
    database_path = app_path / "database"
    models_path = database_path / "models"
    modules_path = app_path / "api" / "modules"


@final
class Config(BaseSettings):
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="APP__",
        env_nested_delimiter="__",
        extra="ignore",
    )

    env: Literal["local", "dev", "prod"] = "local"
    database_url_override: str | None = None
    # Staff uploads live outside the image so they survive a rebuild.
    media_root: Path = Path("media")
    business_timezone: str = "Europe/Kyiv"

    api: APIConfig
    jwt: JwtConfig

    postgres: PostgresConfig
    redis: RedisConfig
    rate_limit: RateLimitConfig = RateLimitConfig()
    nova_poshta: NovaPoshtaConfig = NovaPoshtaConfig()
    outbox: OutboxConfig = OutboxConfig()

    paths: PathsConfig = PathsConfig()

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Config":
        if self.env == "prod" and len(self.jwt.secret_key) < 32:
            raise ValueError(
                "Production JWT secret must contain at least 32 characters"
            )
        try:
            ZoneInfo(self.business_timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("business_timezone must be a valid IANA timezone") from exc
        if self.env == "prod" and (
            "*" in self.api.allowed_origins
            or "*" in self.api.allowed_hosts
            or "*" in self.api.forwarded_allow_ips
        ):
            raise ValueError(
                "Production HTTP origin, host, and proxy lists must be explicit"
            )
        return self

    @property
    def database_url(self) -> str:
        if self.database_url_override:
            return self.database_url_override
        host = "localhost" if self.env == "local" else self.postgres.host
        return URL.build(
            scheme="postgresql+asyncpg",
            user=self.postgres.user,
            password=self.postgres.password,
            host=host,
            port=self.postgres.port,
            path=f"/{self.postgres.db}",
        ).human_repr()

    @property
    def redis_url(self) -> str:
        host = "localhost" if self.env == "local" else self.redis.host
        return URL.build(
            scheme="redis",
            host=host,
            port=self.redis.port,
            path=f"/{self.redis.db}",
        ).human_repr()


@lru_cache
def get_config() -> Config:
    return Config()
