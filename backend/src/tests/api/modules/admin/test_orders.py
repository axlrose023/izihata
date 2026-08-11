import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestAdminOrders:
    endpoint = "/api/v1/admin/orders"

    async def test_lists_orders(
        self,
        client: AsyncClient,
        authenticated_user: dict,
        product,
        order_payload,
        idempotency_key,
    ):
        created = await client.post(
            "/api/v1/orders",
            json=order_payload(product.id),
            headers={"Idempotency-Key": idempotency_key},
        )
        headers = {"Authorization": f"Bearer {authenticated_user['access_token']}"}
        response = await client.get(self.endpoint, headers=headers)

        assert created.status_code == 201
        assert response.status_code == 200, response.text
        assert response.json()["total"] >= 1
        listed = next(
            order
            for order in response.json()["items"]
            if order["id"] == created.json()["id"]
        )
        assert "items" not in listed
        assert listed["total"] == created.json()["total"]

    async def test_updates_status_with_transition_validation(
        self,
        client: AsyncClient,
        authenticated_user: dict,
        product,
        order_payload,
        idempotency_key,
    ):
        created = await client.post(
            "/api/v1/orders",
            json=order_payload(product.id),
            headers={"Idempotency-Key": idempotency_key},
        )
        order_id = created.json()["id"]
        headers = {"Authorization": f"Bearer {authenticated_user['access_token']}"}
        invalid = await client.patch(
            f"{self.endpoint}/{order_id}/status",
            json={"status": "shipped"},
            headers=headers,
        )
        valid = await client.patch(
            f"{self.endpoint}/{order_id}/status",
            json={"status": "processing"},
            headers=headers,
        )

        assert invalid.status_code == 422
        assert valid.status_code == 200
        assert valid.json()["status"] == "processing"

    async def test_supports_the_complete_fulfilment_flow(
        self,
        client: AsyncClient,
        authenticated_user: dict,
        product,
        order_payload,
        idempotency_key,
    ):
        created = await client.post(
            "/api/v1/orders",
            json=order_payload(product.id),
            headers={"Idempotency-Key": idempotency_key},
        )
        headers = {"Authorization": f"Bearer {authenticated_user['access_token']}"}
        order_id = created.json()["id"]

        for status in ["processing", "confirmed", "shipped", "delivered"]:
            response = await client.patch(
                f"{self.endpoint}/{order_id}/status",
                json={"status": status},
                headers=headers,
            )
            assert response.status_code == 200, response.text
            assert response.json()["status"] == status

        cancelled = await client.patch(
            f"{self.endpoint}/{order_id}/status",
            json={"status": "cancelled"},
            headers=headers,
        )
        assert cancelled.status_code == 422

    async def test_requires_authentication(self, client: AsyncClient):
        response = await client.get(self.endpoint)

        assert response.status_code == 401

    async def test_update_returns_not_found(
        self,
        client: AsyncClient,
        authenticated_user: dict,
    ):
        response = await client.patch(
            f"{self.endpoint}/{uuid.uuid4()}/status",
            json={"status": "processing"},
            headers={"Authorization": f"Bearer {authenticated_user['access_token']}"},
        )

        assert response.status_code == 404

    async def test_update_requires_authentication(self, client: AsyncClient):
        response = await client.patch(
            f"{self.endpoint}/{uuid.uuid4()}/status",
            json={"status": "processing"},
        )

        assert response.status_code == 401
