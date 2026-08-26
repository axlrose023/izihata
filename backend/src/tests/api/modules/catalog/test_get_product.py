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
        assert len(body["reviews"]) == 2
        assert body["reviews"][0]["author"]
        assert 1 <= body["reviews"][0]["rating"] <= 5
        assert body["reviews"][0]["text"]

    async def test_returns_not_found(self, client: AsyncClient):
        response = await client.get(f"{self.endpoint}/{uuid.uuid4()}")

        assert response.status_code == 404

    async def test_returns_featured_reviews(self, client: AsyncClient):
        response = await client.get("/api/v1/catalog/reviews/featured")

        assert response.status_code == 200, response.text
        body = response.json()
        assert len(body) == 3
        assert all(1 <= review["rating"] <= 5 for review in body)
        assert all(review["author"] and review["text"] for review in body)

    async def test_returns_enriched_demo_product(self, client: AsyncClient):
        response = await client.get(
            f"{self.endpoint}/demo-modular-circuit-breaker-1p-c16"
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["brand_country"] == "Україна"
        assert body["production_country"] == "Китай"
        assert body["sale_unit"] == "piece"
        assert body["wholesale_min_quantity"] == 5
        assert len(body["media"]) == 2
        assert len(body["documents"]) == 1
        document = body["documents"][0]
        assert document["id"]
        assert document["kind"] == "datasheet"
        assert document["title"] == "Технічна специфікація (демо)"
        assert document["url"] == "/documents/demo-circuit-breaker-specification.pdf"
