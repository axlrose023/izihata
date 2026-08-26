import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient


def customer_payload(**overrides):
    payload = {
        "full_name": "Олена Покупець",
        "email": f"olena-{uuid.uuid4().hex[:8]}@example.com",
        "password": "customer-password-123",
        "phone": "+380671234567",
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
class TestCustomersB2B:
    async def test_registers_customer_and_exposes_isolated_profile(
        self,
        client: AsyncClient,
    ):
        registration = await client.post(
            "/api/v1/customer-auth/register",
            json=customer_payload(),
        )

        assert registration.status_code == 201, registration.text
        assert "izihata_customer_refresh" in registration.cookies
        profile = await client.get(
            "/api/v1/customer/me",
            headers={"Authorization": f"Bearer {registration.json()['access_token']}"},
        )
        assert profile.status_code == 200, profile.text
        assert profile.json()["company"] is None

    async def test_approved_company_receives_authoritative_wholesale_quote(
        self,
        client: AsyncClient,
        authenticated_user: dict,
        product,
    ):
        customer = await client.post(
            "/api/v1/customer-auth/register",
            json=customer_payload(),
        )
        assert customer.status_code == 201, customer.text
        customer_headers = {
            "Authorization": f"Bearer {customer.json()['access_token']}"
        }
        company = await client.post(
            "/api/v1/customer/company",
            json={"kind": "fop", "name": "ФОП Покупець", "edrpou": "12345678"},
            headers=customer_headers,
        )
        assert company.status_code == 201, company.text

        staff_headers = {
            "Authorization": f"Bearer {authenticated_user['access_token']}"
        }
        approved = await client.patch(
            f"/api/v1/admin/customers/companies/{company.json()['id']}",
            json={
                "status": "approved",
                "manager_name": "Менеджер Ірина",
                "cumulative_discount_rate": "0.05",
            },
            headers=staff_headers,
        )
        assert approved.status_code == 200, approved.text
        assert approved.json()["status"] == "approved"

        wholesale_price = product.price / Decimal("2")
        product_update = await client.patch(
            f"/api/v1/admin/catalog/products/{product.id}",
            json={
                "wholesale_price": str(wholesale_price),
                "wholesale_min_quantity": 10,
            },
            headers=staff_headers,
        )
        assert product_update.status_code == 200, product_update.text

        quote = await client.post(
            "/api/v1/checkout/quote",
            json={"items": [{"product_id": str(product.id), "quantity": 1}]},
            headers=customer_headers,
        )
        assert quote.status_code == 200, quote.text
        assert quote.json()["items"][0]["unit_price"] == "45.60"
        assert quote.json()["items"][0]["price_type"] == "wholesale"

        public_product = await client.get(f"/api/v1/catalog/products/{product.slug}")
        assert "wholesale_price" not in public_product.json()
        cleared = await client.patch(
            f"/api/v1/admin/catalog/products/{product.id}",
            json={"wholesale_price": None, "wholesale_min_quantity": None},
            headers=staff_headers,
        )
        assert cleared.status_code == 200, cleared.text

    async def test_customer_order_is_attached_to_order_history(
        self,
        client: AsyncClient,
        product,
    ):
        customer = await client.post(
            "/api/v1/customer-auth/register",
            json=customer_payload(),
        )
        customer_headers = {
            "Authorization": f"Bearer {customer.json()['access_token']}"
        }
        order = await client.post(
            "/api/v1/orders",
            json={
                "items": [{"product_id": str(product.id), "quantity": 1}],
                "customer_name": "Олена Покупець",
                "phone": "+380671234567",
                "delivery": {"method": "pickup"},
                "payment_method": "cash_on_delivery",
            },
            headers={
                **customer_headers,
                "Idempotency-Key": f"customer-order-{uuid.uuid4()}",
            },
        )
        assert order.status_code == 201, order.text

        history = await client.get("/api/v1/customer/orders", headers=customer_headers)
        assert history.status_code == 200, history.text
        assert any(item["id"] == order.json()["id"] for item in history.json()["items"])

    async def test_rejects_duplicate_customer_email(self, client: AsyncClient):
        payload = customer_payload(email="duplicate-customer@example.com")
        first = await client.post("/api/v1/customer-auth/register", json=payload)
        duplicate = await client.post("/api/v1/customer-auth/register", json=payload)

        assert first.status_code == 201, first.text
        assert duplicate.status_code == 409
        assert duplicate.json()["code"] == "customer_email_exists"

    async def test_rotates_and_revokes_customer_session(self, client: AsyncClient):
        registration = await client.post(
            "/api/v1/customer-auth/register",
            json=customer_payload(),
        )
        assert registration.status_code == 201, registration.text

        refreshed = await client.post("/api/v1/customer-auth/refresh")
        assert refreshed.status_code == 200, refreshed.text

        logout = await client.post("/api/v1/customer-auth/logout")
        assert logout.status_code == 204, logout.text
        profile = await client.get(
            "/api/v1/customer/me",
            headers={"Authorization": f"Bearer {refreshed.json()['access_token']}"},
        )
        assert profile.status_code == 401
