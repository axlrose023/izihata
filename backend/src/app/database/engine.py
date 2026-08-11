from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)

from app.settings import Config, get_config

config = get_config()


def create_engine(config: Config) -> AsyncEngine:
    kwargs: dict[str, Any] = {
        "echo": False,
        "pool_pre_ping": True,
    }
    if config.database_url.startswith("postgresql+asyncpg"):
        kwargs.update(
            pool_size=config.postgres.pool_size,
            max_overflow=config.postgres.max_overflow,
            pool_timeout=config.postgres.pool_timeout_seconds,
            pool_recycle=config.postgres.pool_recycle_seconds,
            connect_args={
                "server_settings": {
                    "statement_timeout": str(config.postgres.statement_timeout_ms),
                    "application_name": "izihata-api",
                }
            },
        )
    return create_async_engine(config.database_url, **kwargs)


engine = create_engine(config)

SessionFactory = async_sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)
