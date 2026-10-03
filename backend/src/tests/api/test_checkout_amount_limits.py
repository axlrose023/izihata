from uuid import uuid4

import pytest
from sqlalchemy import delete

from app.api.modules.catalog.models import Product


@pytest.mark.asyncio
async def test_quote_and_order_enforce_database_money_range(
    client, authenticated_user, product, session
):
    headers = {"Authorization": f"Bearer {authenticated_user['access_token']}"}
    created = await client.post(
        "/api/v1/admin/catalog/products",
        headers=headers,
        json={
            "category_id": str(product.category_id),
            "sku": "money-" + uuid4().hex,
            "name": "Money boundary product",
            "brand": product.brand,
            "price": "9999999999.99",
        },
    )
    assert created.status_code == 201, created.text
    try:
        items = [{"product_id": created.json()["id"], "quantity": 2}]
        quote = await client.post("/api/v1/checkout/quote", json={"items": items})
        assert quote.status_code == 422
        assert quote.json()["code"] == "order_total_too_large"
        order = await client.post(
            "/api/v1/orders",
            headers={"Idempotency-Key": str(uuid4())},
            json={
                "items": items,
                "customer_name": "Boundary customer",
                "email": "boundary@example.com",
                "phone": "+380671234567",
                "delivery": {"method": "pickup"},
                "payment_method": "cash_on_delivery",
            },
        )
        assert order.status_code == 422
        assert order.json()["code"] == "order_total_too_large"
        valid = await client.post(
            "/api/v1/checkout/quote", json={"items": [{**items[0], "quantity": 1}]}
        )
        assert valid.status_code == 200
        assert valid.json()["total"] == "9999999999.99"
    finally:
        from uuid import UUID

        await session.execute(
            delete(Product).where(Product.id == UUID(created.json()["id"]))
        )
        await session.commit()
