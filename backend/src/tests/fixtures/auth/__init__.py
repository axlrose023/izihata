from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import AsyncClient

from app.api.modules.auth.utils import REFRESH_COOKIE_NAME
from tests.fixtures.users.admin import user


@pytest_asyncio.fixture
async def authenticated_user(
    client: AsyncClient,
    user,  # noqa: F811
) -> AsyncIterator[dict]:
    """Authenticate user and return tokens."""
    client.cookies.clear()
    login_data = {
        "username": user.username,
        "password": "admin123",
    }
    resp = await client.post("/api/v1/auth/login", json=login_data)
    assert resp.status_code == 200
    payload = resp.json()
    payload["_refresh_token"] = resp.cookies[REFRESH_COOKIE_NAME]
    yield payload
    client.cookies.clear()
