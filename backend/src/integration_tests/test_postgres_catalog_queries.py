"""Queries whose SQL only breaks on PostgreSQL.

The unit suite runs on SQLite, which accepts constructs PostgreSQL rejects
(DISTINCT with an ORDER BY column that is not selected, for one). Catalog
queries that fan out over relations are exercised here against the real engine.
"""

import uuid

import pytest
from sqlalchemy import delete, select

from app.api.modules.catalog.enums import ProductRelationKind
from app.api.modules.catalog.models import Product, ProductRelation
from app.api.modules.catalog.schema import CreateProductRequest, UpdateProductRequest
from app.api.modules.catalog.services.product_management import ProductManagementService
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


@pytest.mark.asyncio(loop_scope="session")
async def test_repeated_collection_edits_preserve_variants_and_unique_positions():
    async with SessionFactory() as session, UnitOfWork(session) as uow:
        base = await session.scalar(select(Product).where(Product.sku == "AX-10001"))
        media = [
            {
                "url": f"https://cdn.example/{index}.jpg",
                "alt": "Photo",
                "position": index,
            }
            for index in range(2)
        ]
        documents = [
            {
                "title": "Certificate",
                "url": "https://cdn.example/file.pdf",
                "position": 0,
            }
        ]
        service = ProductManagementService(uow)
        created = await service.create_product(
            CreateProductRequest.model_validate(
                {
                    "category_id": base.category_id,
                    "sku": "integration-gallery-" + uuid.uuid4().hex,
                    "name": "Gallery regression",
                    "brand": base.brand,
                    "price": "100.00",
                    "media": media,
                    "documents": documents,
                }
            )
        )
        try:
            saved = await uow.products.get_by_id_for_update(created.id)
            for item in saved.media:
                item.image_variants = {
                    "source": item.url,
                    "generator": "webp-v2",
                    "sizes": {"80": item.url + "-small.webp"},
                }
            saved.image_variants = saved.media[0].image_variants
            await uow.commit()
            for ordered in [media, list(reversed(media)), media]:
                await service.update_product(
                    created.id,
                    UpdateProductRequest.model_validate(
                        {
                            "media": [
                                {**item, "position": index}
                                for index, item in enumerate(ordered)
                            ],
                            "documents": documents,
                        }
                    ),
                )
                saved = await uow.products.get_by_id_for_update(created.id)
                assert [item.url for item in saved.media] == [
                    item["url"] for item in ordered
                ]
                assert saved.image_variants["source"] == ordered[0]["url"]
                assert all(
                    item.image_variants["sizes"]["80"] == item.url + "-small.webp"
                    for item in saved.media
                )
                assert len(saved.documents) == 1
        finally:
            await session.execute(delete(Product).where(Product.id == created.id))
            await uow.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_normalized_facet_keys_and_values_execute_on_postgresql():
    import json
    from decimal import Decimal

    from app.api.modules.catalog.models import Category, ProductAttribute
    from app.api.modules.catalog.schema import ProductListParams, SpecFacetParams
    from app.api.modules.catalog.services.catalog_query import CatalogQueryService

    async with SessionFactory() as session, UnitOfWork(session) as uow:
        category = await session.scalar(
            select(Category).where(Category.slug == "panels")
        )
        assert category is not None
        unique = uuid.uuid4().hex
        session.add(
            Product(
                sku=unique,
                slug=unique,
                name="Facet QA",
                brand=unique,
                category_id=category.id,
                price=Decimal("100.00"),
                attributes=[
                    ProductAttribute(key="Матеріал корпусу", value="метал"),
                    ProductAttribute(key="Ступінь захисту", value="44"),
                ],
            )
        )
        await session.flush()
        service = CatalogQueryService(uow)
        keys = await service.get_spec_facets(
            SpecFacetParams(category="panels", brand=[unique])
        )
        assert {item.value: item.count for item in keys.items} == {
            "Матеріал": 0,
            "Ступінь захисту IP": 0,
        }
        for key, value in (("Матеріал", "Метал"), ("Ступінь захисту IP", "IP44")):
            values = await service.get_spec_facets(
                SpecFacetParams(category="panels", brand=[unique], facet_key=key)
            )
            assert [(item.value, item.count) for item in values.items] == [(value, 1)]
            products = await service.get_products(
                ProductListParams(
                    category="panels", brand=[unique], spec=[json.dumps([key, value])]
                )
            )
            assert products.total == 1
        await session.rollback()
