import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from app.api.modules.outbox.models import OutboxEvent


@pytest.mark.asyncio
class TestCreateLead:
    endpoint = "/api/v1/leads"

    async def test_creates_callback_and_outbox_event(self, client: AsyncClient, uow):
        response = await client.post(
            self.endpoint,
            json={
                "type": "callback",
                "name": "Олена",
                "phone": "+380671234567",
            },
        )

        assert response.status_code == 201, response.text
        assert response.json()["status"] == "new"
        count = await uow.session.scalar(
            select(func.count(OutboxEvent.id)).where(
                OutboxEvent.topic == "lead.created"
            )
        )
        assert count >= 1

    async def test_creates_quick_buy_lead(self, client: AsyncClient, product):
        response = await client.post(
            self.endpoint,
            json={
                "type": "quick_buy",
                "name": "Ігор",
                "phone": "+380501234567",
                "product_id": str(product.id),
            },
        )

        assert response.status_code == 201
        assert response.json()["type"] == "quick_buy"

    async def test_requires_company_for_wholesale(self, client: AsyncClient):
        response = await client.post(
            self.endpoint,
            json={
                "type": "wholesale",
                "name": "Марина",
                "phone": "+380931234567",
            },
        )

        assert response.status_code == 422

    async def test_rejects_unknown_product(self, client: AsyncClient):
        response = await client.post(
            self.endpoint,
            json={
                "type": "quick_buy",
                "name": "Ігор",
                "phone": "+380501234567",
                "product_id": str(uuid.uuid4()),
            },
        )

        assert response.status_code == 422

    async def test_rejects_product_for_callback(self, client: AsyncClient, product):
        response = await client.post(
            self.endpoint,
            json={
                "type": "callback",
                "name": "Олена",
                "phone": "+380671234567",
                "product_id": str(product.id),
            },
        )

        assert response.status_code == 422

    async def test_rejects_whitespace_contact_fields(self, client: AsyncClient):
        response = await client.post(
            self.endpoint,
            json={"type": "callback", "name": "   ", "phone": "   "},
        )

        assert response.status_code == 422

    async def test_rejects_non_string_contact_fields(self, client: AsyncClient):
        response = await client.post(
            self.endpoint,
            json={"type": "callback", "name": 123, "phone": 380671234567},
        )

        assert response.status_code == 422

    async def test_accepts_and_normalizes_ukrainian_local_phone(
        self,
        client: AsyncClient,
        authenticated_user: dict,
    ):
        created = await client.post(
            self.endpoint,
            json={"type": "callback", "name": "Олена", "phone": "067 123-45-67"},
        )
        listed = await client.get(
            "/api/v1/admin/leads",
            headers={"Authorization": f"Bearer {authenticated_user['access_token']}"},
        )

        lead = next(
            item
            for item in listed.json()["items"]
            if item["id"] == created.json()["id"]
        )
        assert lead["phone"] == "+380671234567"
