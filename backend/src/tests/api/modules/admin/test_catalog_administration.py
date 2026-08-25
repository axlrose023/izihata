import uuid
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import delete

from app.api.modules.catalog.enums import ReviewStatus
from app.api.modules.catalog.models import CatalogSection, Product, ProductReview
from app.database.uow import UnitOfWork


def headers(tokens: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest.mark.asyncio
class TestCatalogAdministration:
    async def test_manages_catalog_attributes_for_a_category(
        self,
        client: AsyncClient,
        authenticated_user: dict,
        product,
    ):
        token_headers = headers(authenticated_user)
        attribute = await client.post(
            "/api/v1/admin/catalog/attributes",
            json={
                "code": f"nominal_current_{uuid.uuid4().hex[:8]}",
                "name": "Номінальний струм",
                "value_type": "number",
                "unit": "A",
                "is_filterable": True,
            },
            headers=token_headers,
        )
        assert attribute.status_code == 201, attribute.text

        replacement = await client.put(
            f"/api/v1/admin/catalog/categories/{product.category_id}/attributes",
            json={
                "attributes": [
                    {
                        "attribute_id": attribute.json()["id"],
                        "is_required": True,
                        "is_primary_filter": True,
                    }
                ]
            },
            headers=token_headers,
        )
        assert replacement.status_code == 200, replacement.text
        assignment = replacement.json()[0]
        assert assignment["attribute"]["id"] == attribute.json()["id"]
        assert assignment["is_primary_filter"] is True
        reset = await client.put(
            f"/api/v1/admin/catalog/categories/{product.category_id}/attributes",
            json={"attributes": []},
            headers=token_headers,
        )
        assert reset.status_code == 200, reset.text
        assert reset.json() == []

    async def test_manages_sections_and_category_assignment(
        self,
        client: AsyncClient,
        authenticated_user: dict,
        product,
        uow: UnitOfWork,
    ):
        token_headers = headers(authenticated_user)
        section = await client.post(
            "/api/v1/admin/catalog/sections",
            json={
                "slug": f"qa-section-{uuid.uuid4().hex[:8]}",
                "name": "Тестовий розділ",
                "position": 12,
            },
            headers=token_headers,
        )
        assert section.status_code == 201, section.text

        assignment = await client.patch(
            f"/api/v1/admin/catalog/categories/{product.category_id}/section",
            json={"section_id": section.json()["id"]},
            headers=token_headers,
        )
        assert assignment.status_code == 204, assignment.text

        home_section = next(
            item
            for item in (await client.get("/api/v1/catalog/sections")).json()
            if item["slug"] == "home-repair"
        )
        restore = await client.patch(
            f"/api/v1/admin/catalog/categories/{product.category_id}/section",
            json={"section_id": home_section["id"]},
            headers=token_headers,
        )
        assert restore.status_code == 204, restore.text

        update = await client.patch(
            f"/api/v1/admin/catalog/sections/{section.json()['id']}",
            json={"is_active": False},
            headers=token_headers,
        )
        assert update.status_code == 200, update.text
        assert update.json()["is_active"] is False
        await uow.session.execute(
            delete(CatalogSection).where(
                CatalogSection.id == UUID(section.json()["id"])
            )
        )
        await uow.commit()

    async def test_updates_product_media_documents_and_relations(
        self,
        client: AsyncClient,
        authenticated_user: dict,
        product,
        uow: UnitOfWork,
    ):
        token_headers = headers(authenticated_user)
        source = await client.post(
            "/api/v1/admin/catalog/products",
            json={
                "category_id": str(product.category_id),
                "subcategory_id": str(product.subcategory_id),
                "sku": f"QA-{uuid.uuid4().hex[:12]}",
                "name": "Товар для перевірки медіа",
                "brand": "QA Electric",
                "price": "500.00",
            },
            headers=token_headers,
        )
        assert source.status_code == 201, source.text
        response = await client.patch(
            f"/api/v1/admin/catalog/products/{source.json()['id']}",
            json={
                "brand_country": "Франція",
                "production_country": "Україна",
                "sale_unit": "piece",
                "wholesale_price": "100.00",
                "wholesale_min_quantity": 10,
                "media": [
                    {
                        "url": "/product-images/automation-detail.svg",
                        "alt": "Автоматичний вимикач, вигляд спереду",
                    }
                ],
                "documents": [
                    {
                        "kind": "certificate",
                        "title": "Сертифікат відповідності",
                        "url": "/documents/qa-certificate.pdf",
                    }
                ],
                "relations": [{"product_id": str(product.id), "kind": "alternative"}],
            },
            headers=token_headers,
        )
        assert response.status_code == 200, response.text
        assert response.json()["wholesale_min_quantity"] == 10
        assert response.json()["wholesale_price"] == "100.00"

        public = await client.get(f"/api/v1/catalog/products/{source.json()['slug']}")
        assert public.status_code == 200, public.text
        assert public.json()["brand_country"] == "Франція"
        assert public.json()["media"][0]["alt"].startswith("Автоматичний")
        assert public.json()["documents"][0]["kind"] == "certificate"
        assert public.json()["alternatives"][0]["id"] == str(product.id)
        assert "wholesale_price" not in public.json()
        await uow.session.execute(
            delete(Product).where(Product.id == UUID(source.json()["id"]))
        )
        await uow.commit()

    async def test_moderates_submitted_reviews(
        self,
        client: AsyncClient,
        authenticated_user: dict,
        product,
        uow: UnitOfWork,
    ):
        original_rating = product.rating
        original_reviews_count = product.reviews_count
        created = await client.post(
            f"/api/v1/catalog/products/{product.slug}/reviews",
            json={
                "author": "Тестовий покупець",
                "email": "reviewer@example.com",
                "rating": 4,
                "text": "Відгук для перевірки модерації в адміністративній панелі.",
            },
        )
        assert created.status_code == 201, created.text

        reviews = await client.get(
            "/api/v1/admin/catalog/reviews",
            headers=headers(authenticated_user),
        )
        assert reviews.status_code == 200, reviews.text
        review = next(
            item
            for item in reviews.json()["items"]
            if item["id"] == created.json()["id"]
        )
        assert review["status"] == ReviewStatus.PENDING
        assert review["email"] == "reviewer@example.com"

        moderation = await client.patch(
            f"/api/v1/admin/catalog/reviews/{review['id']}",
            json={"status": "published", "is_featured": True},
            headers=headers(authenticated_user),
        )
        assert moderation.status_code == 204, moderation.text

        detail = await client.get(f"/api/v1/catalog/products/{product.slug}")
        assert any(item["id"] == review["id"] for item in detail.json()["reviews"])
        await uow.session.execute(
            delete(ProductReview).where(ProductReview.id == UUID(review["id"]))
        )
        product.rating = original_rating
        product.reviews_count = original_reviews_count
        await uow.commit()

    async def test_product_creation_rejects_missing_wholesale_pair(
        self,
        client: AsyncClient,
        authenticated_user: dict,
        product,
    ):
        response = await client.post(
            "/api/v1/admin/catalog/products",
            json={
                "category_id": str(product.category_id),
                "sku": f"QA-{uuid.uuid4().hex[:12]}",
                "name": "Тестовий товар",
                "brand": "QA",
                "price": "500.00",
                "wholesale_price": "400.00",
            },
            headers=headers(authenticated_user),
        )
        assert response.status_code == 422
