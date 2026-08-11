import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestAdminLeads:
    endpoint = "/api/v1/admin/leads"

    async def test_lists_filtered_leads_and_normalized_contact_data(
        self,
        client: AsyncClient,
        authenticated_user: dict,
    ):
        created = await client.post(
            "/api/v1/leads",
            json={
                "type": "wholesale",
                "name": "  Марина   Іваненко ",
                "phone": "+380 (93) 123-45-67",
                "company": "  Ізі   Хата ",
            },
        )
        headers = {"Authorization": f"Bearer {authenticated_user['access_token']}"}
        response = await client.get(
            self.endpoint,
            params={"type": "wholesale", "status": "new"},
            headers=headers,
        )

        assert created.status_code == 201, created.text
        assert response.status_code == 200, response.text
        lead = next(
            item
            for item in response.json()["items"]
            if item["id"] == created.json()["id"]
        )
        assert lead["name"] == "Марина Іваненко"
        assert lead["phone"] == "+380931234567"
        assert lead["company"] == "Ізі Хата"

    async def test_applies_only_allowed_status_transitions(
        self,
        client: AsyncClient,
        authenticated_user: dict,
    ):
        created = await client.post(
            "/api/v1/leads",
            json={
                "type": "callback",
                "name": "Олена",
                "phone": "+380671234567",
            },
        )
        lead_id = created.json()["id"]
        headers = {"Authorization": f"Bearer {authenticated_user['access_token']}"}

        contacted = await client.patch(
            f"{self.endpoint}/{lead_id}/status",
            json={"status": "contacted"},
            headers=headers,
        )
        closed = await client.patch(
            f"{self.endpoint}/{lead_id}/status",
            json={"status": "closed"},
            headers=headers,
        )
        invalid = await client.patch(
            f"{self.endpoint}/{lead_id}/status",
            json={"status": "contacted"},
            headers=headers,
        )

        assert contacted.status_code == 200
        assert closed.status_code == 200
        assert closed.json()["status"] == "closed"
        assert invalid.status_code == 422

    async def test_returns_not_found(
        self,
        client: AsyncClient,
        authenticated_user: dict,
    ):
        response = await client.patch(
            f"{self.endpoint}/{uuid.uuid4()}/status",
            json={"status": "contacted"},
            headers={"Authorization": f"Bearer {authenticated_user['access_token']}"},
        )

        assert response.status_code == 404

    async def test_requires_authentication(self, client: AsyncClient):
        list_response = await client.get(self.endpoint)
        patch_response = await client.patch(
            f"{self.endpoint}/{uuid.uuid4()}/status",
            json={"status": "contacted"},
        )

        assert list_response.status_code == 401
        assert patch_response.status_code == 401
