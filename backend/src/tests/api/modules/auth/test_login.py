import pytest
from httpx import AsyncClient

from app.api.modules.auth.utils import REFRESH_COOKIE_NAME, REFRESH_COOKIE_PATH


@pytest.mark.asyncio
class TestLogin:
    endpoint = "/api/v1/auth/login"

    async def test_login_success(self, client: AsyncClient, user):
        response = await client.post(
            self.endpoint,
            json={"username": user.username, "password": "admin123"},
        )

        assert response.status_code == 200
        assert response.json()["token_type"] == "bearer"
        assert "refresh_token" not in response.json()
        assert response.cookies[REFRESH_COOKIE_NAME]
        set_cookie = response.headers["set-cookie"]
        assert "HttpOnly" in set_cookie
        assert f"Path={REFRESH_COOKIE_PATH}" in set_cookie
        assert "SameSite=lax" in set_cookie

    async def test_login_rejects_invalid_password(self, client: AsyncClient, user):
        response = await client.post(
            self.endpoint,
            json={"username": user.username, "password": "incorrect"},
        )

        assert response.status_code == 401

    async def test_login_accepts_short_legacy_password_shape(
        self, client: AsyncClient, user
    ):
        response = await client.post(
            self.endpoint,
            json={"username": user.username, "password": "short"},
        )

        assert response.status_code == 401

    async def test_login_rejects_query_credentials(self, client: AsyncClient):
        response = await client.post(
            f"{self.endpoint}?username=admin&password=admin123"
        )

        assert response.status_code == 422
