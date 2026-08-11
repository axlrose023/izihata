import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestGetProducts:
    endpoint = "/api/v1/catalog/products"

    async def test_returns_paginated_products_and_facets(self, client: AsyncClient):
        response = await client.get(self.endpoint)

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["total"] == 72
        assert len(body["items"]) == 10
        assert body["page"] == 1
        assert body["total_pages"] == 8
        assert body["facets"]["brands"]
        assert body["facets"]["specs"]

    async def test_filters_by_category_brand_stock_and_spec(
        self,
        client: AsyncClient,
    ):
        response = await client.get(
            self.endpoint,
            params=[
                ("category", "lowvoltage"),
                ("brand", "IEK"),
                ("in_stock", "true"),
                ("spec", "Полюси:1P"),
            ],
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["sku"] == "AX-10001"

    async def test_search_and_price_sort(self, client: AsyncClient):
        search = await client.get(self.endpoint, params={"search": "RESI9"})
        sorted_response = await client.get(
            self.endpoint,
            params={"category": "cable", "sort": "price_asc", "page_size": 5},
        )

        assert search.status_code == 200
        assert search.json()["total"] == 2
        prices = [float(item["price"]) for item in sorted_response.json()["items"]]
        assert prices == sorted(prices)

    async def test_filters_by_repeated_product_id(self, client: AsyncClient):
        source = await client.get(self.endpoint, params={"page_size": 2})
        expected_ids = [item["id"] for item in source.json()["items"]]

        response = await client.get(
            self.endpoint,
            params=[
                ("id", expected_ids[0]),
                ("id", expected_ids[1]),
                ("id", expected_ids[0]),
                ("page_size", "100"),
            ],
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["total"] == 2
        assert {item["id"] for item in body["items"]} == set(expected_ids)

    async def test_rejects_too_many_product_ids(self, client: AsyncClient):
        response = await client.get(
            self.endpoint,
            params=[("id", str(uuid.uuid4())) for _ in range(101)],
        )

        assert response.status_code == 422

    async def test_rejects_invalid_product_id(self, client: AsyncClient):
        response = await client.get(self.endpoint, params={"id": "invalid"})

        assert response.status_code == 422

    async def test_rejects_invalid_filters(self, client: AsyncClient):
        response = await client.get(
            self.endpoint,
            params={"min_price": 100, "max_price": 10},
        )

        assert response.status_code == 422

    async def test_rejects_invalid_spec_format(self, client: AsyncClient):
        response = await client.get(self.endpoint, params={"spec": "invalid"})

        assert response.status_code == 422
