import pytest
from httpx import AsyncClient

from app.api.modules.auth.utils import REFRESH_COOKIE_NAME, REFRESH_COOKIE_PATH


def set_refresh_cookie(client: AsyncClient, token: str) -> None:
    client.cookies.set(REFRESH_COOKIE_NAME, token, path=REFRESH_COOKIE_PATH)


@pytest.mark.asyncio
class TestRefreshToken:
    endpoint = "/api/v1/auth/refresh"

    async def test_refresh_token_success(
        self,
        client: AsyncClient,
        authenticated_user: dict,
    ):
        original_token = authenticated_user["_refresh_token"]

        response = await client.post(self.endpoint)

        assert response.status_code == 200
        assert response.json()["token_type"] == "bearer"
        assert "access_token" in response.json()
        assert "refresh_token" not in response.json()
        assert response.cookies[REFRESH_COOKIE_NAME] != original_token

    async def test_refresh_token_requires_cookie(self, client: AsyncClient):
        client.cookies.clear()

        response = await client.post(self.endpoint)

        assert response.status_code == 401

    @pytest.mark.parametrize(
        ("token", "expected_status"),
        [
            ("invalid_token", 401),
            ("x" * 4097, 422),
            (
                "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
                "eyJzdWIiOiIxMjM0NTY3ODkwIiwidHlwZSI6InJlZnJlc2giLCJleHAiOjE1MTYyMzkwMjJ9."
                "expired",
                401,
            ),
        ],
    )
    async def test_rejects_invalid_cookie(
        self,
        client: AsyncClient,
        token: str,
        expected_status: int,
    ):
        client.cookies.clear()
        set_refresh_cookie(client, token)

        response = await client.post(self.endpoint)

        assert response.status_code == expected_status

    async def test_rejects_access_token(
        self,
        client: AsyncClient,
        authenticated_user: dict,
    ):
        set_refresh_cookie(client, authenticated_user["access_token"])

        response = await client.post(self.endpoint)

        assert response.status_code == 401

    async def test_rotates_refresh_token_and_rejects_replay(
        self,
        client: AsyncClient,
        authenticated_user: dict,
    ):
        original_token = authenticated_user["_refresh_token"]

        rotated = await client.post(self.endpoint)
        rotated_token = rotated.cookies[REFRESH_COOKIE_NAME]
        set_refresh_cookie(client, original_token)
        replay = await client.post(self.endpoint)
        set_refresh_cookie(client, rotated_token)
        next_rotation = await client.post(self.endpoint)

        assert rotated.status_code == 200
        assert rotated_token != original_token
        assert replay.status_code == 401
        assert next_rotation.status_code == 200
