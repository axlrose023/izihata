import uuid

import pytest
from httpx import AsyncClient

from app.api.modules.catalog.enums import StockStatus


@pytest.mark.asyncio
class TestCreateQuote:
    endpoint = "/api/v1/checkout/quote"

    async def test_calculates_prices_on_server(self, client: AsyncClient, product):
        response = await client.post(
            self.endpoint,
            json={"items": [{"product_id": str(product.id), "quantity": 2}]},
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["subtotal"] == "192.00"
        assert body["discount"] == "0.00"
        assert body["total"] == "192.00"

    async def test_applies_active_promotion(self, client: AsyncClient, product):
        response = await client.post(
            self.endpoint,
            json={
                "items": [{"product_id": str(product.id), "quantity": 2}],
                "promo_code": "znizka10",
            },
        )

        assert response.status_code == 200
        assert response.json()["discount"] == "19.20"
        assert response.json()["total"] == "172.80"

    async def test_rejects_unavailable_product(self, client: AsyncClient):
        response = await client.post(
            self.endpoint,
            json={"items": [{"product_id": str(uuid.uuid4()), "quantity": 1}]},
        )

        assert response.status_code == 422
        assert response.json()["code"] == "products_unavailable"

    async def test_rejects_duplicate_products(self, client: AsyncClient, product):
        item = {"product_id": str(product.id), "quantity": 1}
        response = await client.post(self.endpoint, json={"items": [item, item]})

        assert response.status_code == 422
        assert response.json()["code"] == "duplicate_products"

    async def test_rejects_invalid_promotion(self, client: AsyncClient, product):
        response = await client.post(
            self.endpoint,
            json={
                "items": [{"product_id": str(product.id), "quantity": 1}],
                "promo_code": "unknown",
            },
        )

        assert response.status_code == 422
        assert response.json()["code"] == "promotion_invalid"

    async def test_requires_json_body(self, client: AsyncClient, product):
        response = await client.post(
            self.endpoint,
            params={"product_id": str(product.id), "quantity": 1},
        )

        assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [StockStatus.OUT_OF_STOCK, StockStatus.PREORDER])
async def test_stock_policy_applies_to_quote_and_order(
    client, product, uow, order_payload, idempotency_key, status
):
    original_status = product.stock_status
    product.stock_status = status
    await uow.commit()
    try:
        quote = await client.post(
            "/api/v1/checkout/quote",
            json={"items": [{"product_id": str(product.id), "quantity": 2}]},
        )
        order = await client.post(
            "/api/v1/orders",
            json=order_payload(product.id),
            headers={"Idempotency-Key": idempotency_key},
        )
        if status == StockStatus.OUT_OF_STOCK:
            assert quote.status_code == order.status_code == 422
            assert (
                quote.json()["code"] == order.json()["code"] == "products_unavailable"
            )
        else:
            assert quote.status_code == 200, quote.text
            assert order.status_code == 201, order.text
    finally:
        product.stock_status = original_status
        await uow.commit()
