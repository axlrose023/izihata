import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestGetProduct:
    endpoint = "/api/v1/catalog/products"

    async def test_returns_product(self, client: AsyncClient, product):
        response = await client.get(f"{self.endpoint}/{product.slug}")

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["sku"] == product.sku
        assert body["image_url"] == "/product-images/automation.svg"
        assert body["category"]["slug"] == "lowvoltage"
        assert body["specs"]["Полюси"] == "1P"

    async def test_returns_not_found(self, client: AsyncClient):
        response = await client.get(f"{self.endpoint}/{uuid.uuid4()}")

        assert response.status_code == 404
