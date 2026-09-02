"""Queries whose SQL only breaks on PostgreSQL.

The unit suite runs on SQLite, which accepts constructs PostgreSQL rejects
(DISTINCT with an ORDER BY column that is not selected, for one). Catalog
queries that fan out over relations are exercised here against the real engine.
"""

import pytest
from sqlalchemy import select

from app.api.modules.catalog.enums import ProductRelationKind
from app.api.modules.catalog.models import Product, ProductRelation
from app.database.engine import SessionFactory
from app.database.uow import UnitOfWork

pytestmark = pytest.mark.integration


@pytest.mark.asyncio(loop_scope="session")
async def test_recommendations_dedupe_and_exclude_the_basket():
    async with SessionFactory() as session, UnitOfWork(session) as uow:
        source_ids = (
            (
                await session.execute(
                    select(ProductRelation.source_product_id)
                    .where(ProductRelation.kind == ProductRelationKind.BOUGHT_TOGETHER)
                    .limit(2)
                )
            )
            .scalars()
            .all()
        )
        assert source_ids, "demo seed must provide bought-together relations"

        recommended = await uow.products.list_related_to_any(
            set(source_ids),
            ProductRelationKind.BOUGHT_TOGETHER,
        )

        assert recommended
        recommended_ids = [product.id for product in recommended]
        assert len(recommended_ids) == len(set(recommended_ids))
        assert not set(recommended_ids) & set(source_ids)
        # Eager loads must be usable without a second round trip.
        assert all(product.category.slug for product in recommended)


@pytest.mark.asyncio(loop_scope="session")
async def test_recommendations_are_empty_without_sources():
    async with SessionFactory() as session, UnitOfWork(session) as uow:
        assert (
            await uow.products.list_related_to_any(
                set(),
                ProductRelationKind.BOUGHT_TOGETHER,
            )
            == []
        )


@pytest.mark.asyncio(loop_scope="session")
async def test_admin_product_detail_loads_relations():
    async with SessionFactory() as session, UnitOfWork(session) as uow:
        product_id = (
            await session.execute(select(ProductRelation.source_product_id).limit(1))
        ).scalar_one()
        relations = await uow.products.list_relations(product_id)

        assert relations
        assert all(
            isinstance(target, Product) and relation.kind is not None
            for relation, target in relations
        )
