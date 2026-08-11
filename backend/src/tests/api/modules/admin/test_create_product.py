import uuid
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import delete

from app.api.modules.catalog.models import Product
from app.database.uow import UnitOfWork


def product_payload(product, **overrides):
    payload = {
        "category_id": str(product.category_id),
        "subcategory_id": str(product.subcategory_id),
        "sku": f"QA-{uuid.uuid4().hex[:10]}",
        "name": "Тестовий автоматичний вимикач",
        "brand": "QA Electric",
        "image_url": "/product-images/automation.svg",
        "price": "321.50",
        "old_price": "350.00",
        "badge": "new",
        "stock_status": "in_stock",
        "specs": {"Полюси": "2P", "Номінал": "20 А"},
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
class TestCreateProduct:
    endpoint = "/api/v1/admin/catalog/products"

    async def test_creates_product_available_through_public_api(
        self,
        client: AsyncClient,
        authenticated_user: dict,
        product,
        uow: UnitOfWork,
    ):
        payload = product_payload(product, sku=" qa-api-20001 ")
        response = await client.post(
            self.endpoint,
            json=payload,
            headers={"Authorization": f"Bearer {authenticated_user['access_token']}"},
        )

        assert response.status_code == 201, response.text
        body = response.json()
        assert body["sku"] == "QA-API-20001"
        assert body["slug"] == "qa-api-20001"
        assert body["specs"] == payload["specs"]
        assert body["category"]["id"] == payload["category_id"]

        public_response = await client.get(f"/api/v1/catalog/products/{body['slug']}")
        assert public_response.status_code == 200
        assert public_response.json()["id"] == body["id"]

        await uow.session.execute(delete(Product).where(Product.id == UUID(body["id"])))
        await uow.commit()

    async def test_requires_authentication(self, client: AsyncClient, product):
        response = await client.post(self.endpoint, json=product_payload(product))

        assert response.status_code == 401

    async def test_rejects_duplicate_sku(
        self,
        client: AsyncClient,
        authenticated_user: dict,
        product,
    ):
        response = await client.post(
            self.endpoint,
            json=product_payload(product, sku=product.sku.lower()),
            headers={"Authorization": f"Bearer {authenticated_user['access_token']}"},
        )

        assert response.status_code == 409
        assert response.json()["code"] == "product_sku_exists"

    async def test_rejects_subcategory_from_another_category(
        self,
        client: AsyncClient,
        authenticated_user: dict,
        product,
    ):
        categories = (await client.get("/api/v1/catalog/categories")).json()
        other = next(
            item for item in categories if item["id"] != str(product.category_id)
        )
        response = await client.post(
            self.endpoint,
            json=product_payload(product, category_id=other["id"]),
            headers={"Authorization": f"Bearer {authenticated_user['access_token']}"},
        )

        assert response.status_code == 422
        assert response.json()["code"] == "subcategory_category_mismatch"

    async def test_returns_not_found_for_unknown_category(
        self,
        client: AsyncClient,
        authenticated_user: dict,
        product,
    ):
        response = await client.post(
            self.endpoint,
            json=product_payload(product, category_id=str(uuid.uuid4())),
            headers={"Authorization": f"Bearer {authenticated_user['access_token']}"},
        )

        assert response.status_code == 404
        assert response.json()["code"] == "category_not_found"

    @pytest.mark.parametrize(
        ("overrides", "expected_status"),
        [
            ({"old_price": "1.00"}, 422),
            ({"image_url": "javascript:alert(1)"}, 422),
            ({"specs": {"": "value"}}, 422),
            ({"sku": "КИРИЛИЦЯ-1"}, 422),
        ],
    )
    async def test_validates_payload(
        self,
        client: AsyncClient,
        authenticated_user: dict,
        product,
        overrides: dict,
        expected_status: int,
    ):
        response = await client.post(
            self.endpoint,
            json=product_payload(product, **overrides),
            headers={"Authorization": f"Bearer {authenticated_user['access_token']}"},
        )

        assert response.status_code == expected_status
