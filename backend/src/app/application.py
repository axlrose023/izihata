import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from dishka.integrations.fastapi import setup_dishka
from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api import register_routers
from app.api.common.error_handlers import register_error_handlers
from app.database.engine import engine
from app.ioc import get_async_container
from app.services.logging import setup_logging
from app.settings import get_config

config = get_config()
setup_logging(config.env)
logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", include_in_schema=False)
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready", include_in_schema=False)
async def readiness(request: Request) -> JSONResponse:
    try:
        container = request.state.dishka_container
        session: AsyncSession = await container.get(AsyncSession)
        await session.execute(text("SELECT 1"))
        if config.rate_limit.enabled:
            redis: Redis = await container.get(Redis)
            await redis.ping()
    except (SQLAlchemyError, RedisError, ConnectionError, TimeoutError):
        logger.exception("Readiness check failed")
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    return JSONResponse(status_code=200, content={"status": "ready"})


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("Starting application...")
    try:
        yield
    finally:
        await engine.dispose()
        logger.info("Shutting down application...")


def get_production_app() -> FastAPI:
    """Get the FastAPI application instance."""
    app = FastAPI(
        title=config.api.title,
        version=config.api.version,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.api.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=config.api.allowed_hosts)

    api_router = APIRouter(prefix=config.api.prefix)
    register_routers(api_router)
    app.include_router(api_router)
    app.include_router(router)
    register_error_handlers(app)

    setup_dishka(get_async_container(), app)

    # Setup Prometheus metrics
    instrumentator = Instrumentator()
    instrumentator.instrument(app).expose(app, include_in_schema=False)

    return app
