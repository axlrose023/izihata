from uuid import uuid4

import pytest


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "temporary_product", [{"price": "9999999999.99"}], indirect=True
)
async def test_quote_and_order_enforce_database_money_range(client, temporary_product):
    items = [{"product_id": temporary_product["id"], "quantity": 2}]
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
