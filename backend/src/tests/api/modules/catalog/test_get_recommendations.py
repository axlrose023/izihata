import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, select

from app.api.modules.catalog.enums import ProductRelationKind
from app.api.modules.catalog.models import Product, ProductRelation
from app.database.uow import UnitOfWork


@pytest.mark.asyncio
class TestGetRecommendations:
    endpoint = "/api/v1/catalog/recommendations"

    @staticmethod
    async def _reset(uow: UnitOfWork, source: Product) -> None:
        """The suite shares one database, so start from a known relation set."""
        await uow.session.execute(
            delete(ProductRelation).where(
                ProductRelation.source_product_id == source.id
            )
        )
        await uow.commit()

    async def _companion(self, uow: UnitOfWork, source: Product) -> Product:
        await self._reset(uow, source)
        target = (
            await uow.session.execute(
                select(Product).where(Product.id != source.id).limit(1)
            )
        ).scalar_one()
        uow.session.add(
            ProductRelation(
                source_product_id=source.id,
                target_product_id=target.id,
                kind=ProductRelationKind.BOUGHT_TOGETHER,
                position=0,
            )
        )
        await uow.commit()
        return target

    async def test_returns_curated_companions(
        self,
        client: AsyncClient,
        uow: UnitOfWork,
        product: Product,
    ):
        target = await self._companion(uow, product)

        response = await client.get(self.endpoint, params={"id": str(product.id)})

        assert response.status_code == 200, response.text
        body = response.json()
        assert [item["id"] for item in body] == [str(target.id)]
        assert body[0]["category"]["slug"]

    async def test_never_recommends_what_is_already_in_the_basket(
        self,
        client: AsyncClient,
        uow: UnitOfWork,
        product: Product,
    ):
        target = await self._companion(uow, product)

        response = await client.get(
            self.endpoint,
            params={"id": [str(product.id), str(target.id)]},
        )

        assert response.status_code == 200, response.text
        assert response.json() == []

    async def test_returns_empty_for_unrelated_products(
        self,
        client: AsyncClient,
        uow: UnitOfWork,
        product: Product,
    ):
        await self._reset(uow, product)

        response = await client.get(self.endpoint, params={"id": str(product.id)})

        assert response.status_code == 200, response.text
        assert response.json() == []

    async def test_rejects_a_malformed_identifier(self, client: AsyncClient):
        response = await client.get(self.endpoint, params={"id": "not-a-uuid"})

        assert response.status_code == 422

    async def test_requires_at_least_one_identifier(self, client: AsyncClient):
        response = await client.get(self.endpoint)

        assert response.status_code == 422

    async def test_ignores_unknown_identifiers(self, client: AsyncClient):
        response = await client.get(self.endpoint, params={"id": str(uuid.uuid4())})

        assert response.status_code == 200
        assert response.json() == []
