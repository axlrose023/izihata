import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestUpdateProduct:
    endpoint = "/api/v1/admin/catalog/products"

    async def test_updates_price_and_stock(
        self,
        client: AsyncClient,
        authenticated_user: dict,
        product,
    ):
        headers = {"Authorization": f"Bearer {authenticated_user['access_token']}"}
        response = await client.patch(
            f"{self.endpoint}/{product.id}",
            json={"price": "97.00", "stock_status": "preorder"},
            headers=headers,
        )

        assert response.status_code == 200, response.text
        assert response.json()["price"] == "97.00"
        assert response.json()["stock_status"] == "preorder"

        restored = await client.patch(
            f"{self.endpoint}/{product.id}",
            json={"price": "96.00", "stock_status": "in_stock"},
            headers=headers,
        )
        assert restored.status_code == 200

    async def test_rejects_empty_patch(
        self,
        client: AsyncClient,
        authenticated_user: dict,
        product,
    ):
        response = await client.patch(
            f"{self.endpoint}/{product.id}",
            json={},
            headers={"Authorization": f"Bearer {authenticated_user['access_token']}"},
        )

        assert response.status_code == 422

    @pytest.mark.parametrize("field", ["price", "stock_status"])
    async def test_rejects_null_for_required_product_fields(
        self,
        client: AsyncClient,
        authenticated_user: dict,
        product,
        field: str,
    ):
        response = await client.patch(
            f"{self.endpoint}/{product.id}",
            json={field: None},
            headers={"Authorization": f"Bearer {authenticated_user['access_token']}"},
        )

        assert response.status_code == 422

    async def test_requires_authentication(self, client: AsyncClient, product):
        response = await client.patch(
            f"{self.endpoint}/{product.id}",
            json={"price": "100.00"},
        )

        assert response.status_code == 401

    async def test_returns_not_found(
        self,
        client: AsyncClient,
        authenticated_user: dict,
    ):
        response = await client.patch(
            f"{self.endpoint}/{uuid.uuid4()}",
            json={"price": "100.00"},
            headers={"Authorization": f"Bearer {authenticated_user['access_token']}"},
        )

        assert response.status_code == 404
