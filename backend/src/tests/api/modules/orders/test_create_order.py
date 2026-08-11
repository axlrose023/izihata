import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestCreateOrder:
    endpoint = "/api/v1/orders"

    async def test_creates_order_with_server_totals(
        self,
        client: AsyncClient,
        product,
        order_payload,
        idempotency_key,
    ):
        response = await client.post(
            self.endpoint,
            json=order_payload(product.id),
            headers={"Idempotency-Key": idempotency_key},
        )

        assert response.status_code == 201, response.text
        body = response.json()
        assert body["number"].startswith("IZI-")
        assert body["subtotal"] == "192.00"
        assert body["total"] == "192.00"
        assert body["status"] == "new"
        assert body["payment_status"] == "not_required"

    async def test_is_idempotent_for_same_payload(
        self,
        client: AsyncClient,
        product,
        order_payload,
        idempotency_key,
    ):
        payload = order_payload(product.id)
        headers = {"Idempotency-Key": idempotency_key}
        first = await client.post(self.endpoint, json=payload, headers=headers)
        second = await client.post(self.endpoint, json=payload, headers=headers)

        assert first.status_code == second.status_code == 201
        assert first.json()["id"] == second.json()["id"]

    async def test_rejects_reused_key_for_changed_payload(
        self,
        client: AsyncClient,
        product,
        order_payload,
        idempotency_key,
    ):
        headers = {"Idempotency-Key": idempotency_key}
        first = await client.post(
            self.endpoint,
            json=order_payload(product.id),
            headers=headers,
        )
        changed = order_payload(product.id)
        changed["items"][0]["quantity"] = 3
        second = await client.post(self.endpoint, json=changed, headers=headers)

        assert first.status_code == 201
        assert second.status_code == 409

    async def test_requires_idempotency_header(
        self,
        client: AsyncClient,
        product,
        order_payload,
    ):
        response = await client.post(self.endpoint, json=order_payload(product.id))

        assert response.status_code == 422

    async def test_rejects_client_total(
        self,
        client: AsyncClient,
        product,
        order_payload,
        idempotency_key,
    ):
        payload = order_payload(product.id)
        payload["total"] = "0.01"
        response = await client.post(
            self.endpoint,
            json=payload,
            headers={"Idempotency-Key": idempotency_key},
        )

        assert response.status_code == 422

    async def test_invoice_requires_company(
        self,
        client: AsyncClient,
        product,
        order_payload,
        idempotency_key,
    ):
        payload = order_payload(product.id, payment_method="invoice")
        response = await client.post(
            self.endpoint,
            json=payload,
            headers={"Idempotency-Key": idempotency_key},
        )

        assert response.status_code == 422

    @pytest.mark.parametrize(
        ("delivery", "payment_method", "company", "payment_status"),
        [
            (
                {"method": "nova_poshta_branch", "city": "Київ", "point": "1"},
                "cash_on_delivery",
                None,
                "not_required",
            ),
            (
                {"method": "nova_poshta_locker", "city": "Київ", "point": "2"},
                "card",
                None,
                "pending",
            ),
            (
                {"method": "pickup"},
                "invoice",
                {"name": "ТОВ Ізі Хата", "edrpou": "12345678"},
                "pending",
            ),
        ],
    )
    async def test_supports_reference_checkout_variants(
        self,
        client: AsyncClient,
        product,
        order_payload,
        idempotency_key,
        delivery: dict,
        payment_method: str,
        company: dict | None,
        payment_status: str,
    ):
        payload = order_payload(
            product.id,
            delivery=delivery,
            payment_method=payment_method,
        )
        if company:
            payload["company"] = company

        response = await client.post(
            self.endpoint,
            json=payload,
            headers={"Idempotency-Key": idempotency_key},
        )

        assert response.status_code == 201, response.text
        assert response.json()["delivery"]["method"] == delivery["method"]
        assert response.json()["payment_status"] == payment_status

    async def test_normalizes_customer_and_delivery_data(
        self,
        client: AsyncClient,
        product,
        order_payload,
        idempotency_key,
    ):
        payload = order_payload(product.id)
        payload["customer_name"] = "  Олена   Тест "
        payload["phone"] = "+380 (67) 123-45-67"
        payload["delivery"]["city"] = "  Київ "

        response = await client.post(
            self.endpoint,
            json=payload,
            headers={"Idempotency-Key": idempotency_key},
        )

        assert response.status_code == 201, response.text
        assert response.json()["customer_name"] == "Олена Тест"
        assert response.json()["phone"] == "+380671234567"
        assert response.json()["delivery"]["city"] == "Київ"
