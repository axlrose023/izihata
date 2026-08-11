import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestDashboard:
    endpoint = "/api/v1/admin/dashboard"

    async def test_returns_real_aggregates(
        self,
        client: AsyncClient,
        authenticated_user: dict,
    ):
        response = await client.get(
            self.endpoint,
            headers={"Authorization": f"Bearer {authenticated_user['access_token']}"},
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["active_products"] == 72
        assert int(body["orders_today"]) >= 0
        assert "revenue_last_7_days" in body
        assert "new_leads" in body

    async def test_requires_authentication(self, client: AsyncClient):
        response = await client.get(self.endpoint)

        assert response.status_code == 401
