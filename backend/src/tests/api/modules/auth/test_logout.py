from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from httpx import AsyncClient

from app.api.modules.auth.utils import REFRESH_COOKIE_NAME, REFRESH_COOKIE_PATH
from app.settings import get_config


def signed_refresh_token(*, subject: str, session_id: str | None = None) -> str:
    config = get_config()
    return jwt.encode(
        {
            "sub": subject,
            "sid": session_id or str(uuid4()),
            "jti": str(uuid4()),
            "type": "refresh",
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        config.jwt.secret_key,
        algorithm=config.jwt.algorithm,
    )


def set_refresh_cookie(client: AsyncClient, token: str) -> None:
    client.cookies.set(REFRESH_COOKIE_NAME, token, path=REFRESH_COOKIE_PATH)


@pytest.mark.asyncio
class TestLogout:
    endpoint = "/api/v1/auth/logout"

    async def test_revokes_refresh_and_access_tokens(
        self,
        client: AsyncClient,
        authenticated_user: dict,
    ):
        response = await client.post(self.endpoint)
        set_refresh_cookie(client, authenticated_user["_refresh_token"])
        refresh = await client.post("/api/v1/auth/refresh")
        dashboard = await client.get(
            "/api/v1/admin/dashboard",
            headers={"Authorization": f"Bearer {authenticated_user['access_token']}"},
        )

        assert response.status_code == 204
        assert not response.content
        assert refresh.status_code == 401
        assert dashboard.status_code == 401
        assert f'{REFRESH_COOKIE_NAME}=""' in response.headers["set-cookie"]

    async def test_is_idempotent(
        self,
        client: AsyncClient,
        authenticated_user: dict,
    ):
        first = await client.post(self.endpoint)
        second = await client.post(self.endpoint)

        assert first.status_code == 204
        assert second.status_code == 204

    async def test_rotated_token_can_revoke_current_session(
        self,
        client: AsyncClient,
        authenticated_user: dict,
    ):
        original_token = authenticated_user["_refresh_token"]
        rotated = await client.post("/api/v1/auth/refresh")
        rotated_token = rotated.cookies[REFRESH_COOKIE_NAME]

        set_refresh_cookie(client, original_token)
        logout = await client.post(self.endpoint)
        set_refresh_cookie(client, rotated_token)
        current_refresh = await client.post("/api/v1/auth/refresh")

        assert rotated.status_code == 200
        assert logout.status_code == 204
        assert current_refresh.status_code == 401

    async def test_missing_cookie_is_already_logged_out(self, client: AsyncClient):
        client.cookies.clear()

        response = await client.post(self.endpoint)

        assert response.status_code == 204

    @pytest.mark.parametrize(
        ("token", "expected_status"),
        [("invalid-token", 401), ("x" * 4097, 422)],
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

    async def test_rejects_signed_token_with_malformed_identity(
        self,
        client: AsyncClient,
    ):
        set_refresh_cookie(client, signed_refresh_token(subject="not-a-uuid"))

        response = await client.post(self.endpoint)

        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid refresh token payload"

    async def test_unknown_signed_session_is_already_logged_out(
        self,
        client: AsyncClient,
    ):
        set_refresh_cookie(client, signed_refresh_token(subject=str(uuid4())))

        response = await client.post(self.endpoint)

        assert response.status_code == 204
