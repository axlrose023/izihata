import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.common.error_handlers import register_error_handlers


@pytest.mark.asyncio
async def test_unknown_route_returns_json_404(client: AsyncClient):
    response = await client.get("/api/v1/unknown")

    assert response.status_code == 404
    assert response.json() == {"code": "not_found", "detail": "Not Found"}


@pytest.mark.asyncio
async def test_unsupported_method_returns_json_405(client: AsyncClient):
    response = await client.post("/health")

    assert response.status_code == 405
    assert response.json() == {
        "code": "method_not_allowed",
        "detail": "Method Not Allowed",
    }
    assert "GET" in response.headers["allow"]


@pytest.mark.asyncio
async def test_malformed_json_returns_validation_error(client: AsyncClient):
    response = await client.post(
        "/api/v1/checkout/quote",
        content="{invalid",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)
    assert response.json()["code"] == "validation_error"


@pytest.mark.asyncio
async def test_unexpected_error_is_sanitized():
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("private diagnostic details")

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        response = await client.get("/boom")

    assert response.status_code == 500
    assert response.json() == {
        "code": "internal_error",
        "detail": "Internal server error",
    }
    assert "private diagnostic details" not in response.text
