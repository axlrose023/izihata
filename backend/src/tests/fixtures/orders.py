import uuid

import pytest


@pytest.fixture
def order_payload():
    def build(product_id, **overrides):
        payload = {
            "items": [{"product_id": str(product_id), "quantity": 2}],
            "customer_name": "Олена Тест",
            "phone": "+380671234567",
            "delivery": {
                "method": "nova_poshta_branch",
                "city": "Київ",
                "point": "Відділення №1",
            },
            "payment_method": "cash_on_delivery",
        }
        payload.update(overrides)
        return payload

    return build


@pytest.fixture
def idempotency_key() -> str:
    return f"test-{uuid.uuid4()}"
