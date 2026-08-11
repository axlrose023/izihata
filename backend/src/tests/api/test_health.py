import pytest
from httpx import AsyncClient
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_readiness(client: AsyncClient):
    response = await client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


@pytest.mark.asyncio
async def test_readiness_reports_database_failure(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    async def unavailable(*args: object, **kwargs: object) -> None:
        raise SQLAlchemyError("database unavailable")

    monkeypatch.setattr(AsyncSession, "execute", unavailable)

    response = await client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}


@pytest.mark.asyncio
async def test_metrics(client: AsyncClient):
    response = await client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "http_requests_total" in response.text
