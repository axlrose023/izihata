from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.api.modules.catalog.enums import (
    ReviewStatus,
    StockStatus,
    StockSubscriptionStatus,
)
from app.api.modules.catalog.models import ProductReview, ProductStockSubscription
from app.api.modules.outbox.models import OutboxEvent
from app.database.uow import UnitOfWork


@pytest.mark.asyncio
class TestCatalogExtensions:
    async def test_lists_seeded_sections_and_filters_products_by_section(
        self,
        client: AsyncClient,
    ):
        sections_response = await client.get("/api/v1/catalog/sections")
        products_response = await client.get(
            "/api/v1/catalog/products",
            params={"section": "energy-independence"},
        )

        assert sections_response.status_code == 200, sections_response.text
        assert [section["slug"] for section in sections_response.json()] == [
            "home-repair",
            "business-objects",
            "energy-independence",
        ]
        assert products_response.status_code == 200, products_response.text
        assert products_response.json()["total"] > 0
        assert "availability" in products_response.json()["facets"]
        assert "sale_units" in products_response.json()["facets"]

    async def test_submits_unpublished_review_and_emits_manager_event(
        self,
        client: AsyncClient,
        product,
        uow: UnitOfWork,
    ):
        response = await client.post(
            f"/api/v1/catalog/products/{product.slug}/reviews",
            json={
                "author": "Марія Покупець",
                "email": "Maria@example.com",
                "rating": 5,
                "text": "Якісний товар, монтаж пройшов без проблем.",
            },
        )

        assert response.status_code == 201, response.text
        review_id = UUID(response.json()["id"])
        assert response.json()["status"] == ReviewStatus.PENDING
        review = await uow.session.get(ProductReview, review_id)
        assert review is not None
        assert review.email == "maria@example.com"
        assert review.is_published is False
        event = (
            await uow.session.execute(
                select(OutboxEvent).where(
                    OutboxEvent.topic == "catalog.review_submitted",
                    OutboxEvent.payload["review_id"].as_string() == str(review_id),
                )
            )
        ).scalar_one()
        assert event.payload == {
            "review_id": str(review_id),
            "product_id": str(product.id),
        }

    async def test_subscribes_and_queues_stock_notification_after_restock(
        self,
        client: AsyncClient,
        authenticated_user: dict,
        product,
        uow: UnitOfWork,
    ):
        headers = {"Authorization": f"Bearer {authenticated_user['access_token']}"}
        unavailable = await client.patch(
            f"/api/v1/admin/catalog/products/{product.id}",
            json={"stock_status": StockStatus.OUT_OF_STOCK},
            headers=headers,
        )
        assert unavailable.status_code == 200, unavailable.text

        subscription_response = await client.post(
            f"/api/v1/catalog/products/{product.slug}/stock-subscriptions",
            json={"email": "notify@example.com"},
        )
        assert subscription_response.status_code == 201, subscription_response.text

        restocked = await client.patch(
            f"/api/v1/admin/catalog/products/{product.id}",
            json={"stock_status": StockStatus.IN_STOCK_TODAY},
            headers=headers,
        )
        assert restocked.status_code == 200, restocked.text

        subscription = await uow.session.get(
            ProductStockSubscription,
            UUID(subscription_response.json()["id"]),
        )
        assert subscription is not None
        assert subscription.status == StockSubscriptionStatus.NOTIFIED
        event = (
            await uow.session.execute(
                select(OutboxEvent).where(OutboxEvent.topic == "catalog.back_in_stock")
            )
        ).scalar_one()
        assert event.payload["subscription_id"] == str(subscription.id)
        assert event.payload["product_id"] == str(product.id)

    async def test_rejects_stock_subscription_for_available_product(
        self,
        client: AsyncClient,
        product,
    ):
        response = await client.post(
            f"/api/v1/catalog/products/{product.slug}/stock-subscriptions",
            json={"email": "notify@example.com"},
        )

        assert response.status_code == 422
        assert response.json()["code"] == "product_is_available"
