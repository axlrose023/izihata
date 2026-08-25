from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.api.modules.custom_boards.enums import BoardRequestStatus
from app.api.modules.custom_boards.models import CustomBoardRequest
from app.api.modules.outbox.models import OutboxEvent
from app.database.uow import UnitOfWork


@pytest.mark.asyncio
class TestCustomBoards:
    async def test_estimates_configuration_without_background_task(
        self,
        client: AsyncClient,
    ):
        response = await client.post(
            "/api/v1/custom-boards/estimate",
            json={
                "application": "house",
                "groups_count": 5,
                "ip_class": "ip54",
            },
        )

        assert response.status_code == 200, response.text
        assert response.json()["starting_price"] == "2500.00"
        assert response.json()["response_sla_hours"] == 24
        assert response.json()["suggested_components"]

    async def test_creates_board_request_and_outbox_manager_event(
        self,
        client: AsyncClient,
        uow: UnitOfWork,
    ):
        response = await client.post(
            "/api/v1/custom-boards/requests",
            json={
                "customer_name": "Олена Тест",
                "phone": "067 123 45 67",
                "email": "Board@example.com",
                "application": "apartment",
                "groups_count": 8,
                "ip_class": "IP41",
                "automation_brand": "Schneider Electric",
                "budget": "10000.00",
            },
        )

        assert response.status_code == 201, response.text
        request_id = UUID(response.json()["id"])
        board_request = await uow.session.get(CustomBoardRequest, request_id)
        assert board_request is not None
        assert board_request.phone == "+380671234567"
        assert board_request.email == "board@example.com"
        assert board_request.estimated_from_price == 4000
        event = (
            await uow.session.execute(
                select(OutboxEvent).where(
                    OutboxEvent.topic == "custom_boards.request_created",
                    OutboxEvent.payload["request_id"].as_string() == str(request_id),
                )
            )
        ).scalar_one()
        assert event.payload == {"request_id": str(request_id)}

    async def test_admin_moves_request_through_valid_state_machine(
        self,
        client: AsyncClient,
        authenticated_user: dict,
        uow: UnitOfWork,
    ):
        created = await client.post(
            "/api/v1/custom-boards/requests",
            json={
                "customer_name": "Максим Тест",
                "phone": "+380501234567",
                "application": "industrial",
                "groups_count": 12,
                "ip_class": "IP54",
            },
        )
        request_id = created.json()["id"]
        headers = {"Authorization": f"Bearer {authenticated_user['access_token']}"}

        invalid = await client.patch(
            f"/api/v1/admin/custom-boards/requests/{request_id}",
            json={"status": "quoted"},
            headers=headers,
        )
        assert invalid.status_code == 422
        assert invalid.json()["code"] == "invalid_custom_board_status_transition"

        in_progress = await client.patch(
            f"/api/v1/admin/custom-boards/requests/{request_id}",
            json={"status": "in_progress"},
            headers=headers,
        )
        quoted = await client.patch(
            f"/api/v1/admin/custom-boards/requests/{request_id}",
            json={"status": "quoted"},
            headers=headers,
        )
        assert in_progress.status_code == 204, in_progress.text
        assert quoted.status_code == 204, quoted.text
        board_request = await uow.session.get(CustomBoardRequest, UUID(request_id))
        assert board_request is not None
        assert board_request.status == BoardRequestStatus.QUOTED

    async def test_admin_publishes_portfolio_item(
        self, client: AsyncClient, authenticated_user
    ):
        headers = {"Authorization": f"Bearer {authenticated_user['access_token']}"}
        created = await client.post(
            "/api/v1/admin/custom-boards/portfolio",
            json={
                "title": "Щит для приватного будинку",
                "description": "Щит з резервним живленням та захистом ліній.",
                "image_url": "/portfolio/board-house.webp",
            },
            headers=headers,
        )
        assert created.status_code == 201, created.text

        public = await client.get("/api/v1/custom-boards/portfolio")
        assert public.status_code == 200, public.text
        assert any(item["id"] == created.json()["id"] for item in public.json())
