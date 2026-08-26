import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestGetCategories:
    endpoint = "/api/v1/catalog/categories"

    async def test_returns_reference_catalog(self, client: AsyncClient):
        response = await client.get(self.endpoint)

        assert response.status_code == 200
        categories = response.json()
        assert len(categories) == 18
        assert sum(category["product_count"] for category in categories) == 73
        low_voltage = next(item for item in categories if item["slug"] == "lowvoltage")
        assert low_voltage["product_count"] == 12
        assert len(low_voltage["subcategories"]) == 14

    async def test_rejects_wrong_method(self, client: AsyncClient):
        response = await client.post(self.endpoint, json={})

        assert response.status_code == 405
