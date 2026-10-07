import json
from collections.abc import AsyncIterator
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import event, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.common.exceptions import UnprocessableError
from app.api.modules.catalog.enums import ProductAttributeSource, StockStatus
from app.api.modules.catalog.models import (
    CatalogAttribute,
    Category,
    CategoryAttribute,
    Product,
    ProductAttribute,
)
from app.api.modules.catalog.schema import (
    ProductListParams,
    SpecFacetParams,
    UpdateProductRequest,
)
from app.api.modules.catalog.services.catalog_query import CatalogQueryService
from app.api.modules.catalog.services.product_management import ProductManagementService
from app.database.base import Base
from app.database.seed.category_filters import configure_category_filters
from app.database.uow import UnitOfWork

CURRENT = "Номінальний струм"
CODE = "Код виробника"
EXTRA = "Додаткова характеристика постачальника"


@pytest_asyncio.fixture
async def filter_uow() -> AsyncIterator[UnitOfWork]:
    engine = create_async_engine("sqlite+aiosqlite://")

    @event.listens_for(engine.sync_engine, "connect")
    def enable_foreign_keys(connection, _) -> None:
        connection.execute("PRAGMA foreign_keys = ON")

    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            categories = {
                slug: Category(id=uuid4(), slug=slug, name=slug)
                for slug in ("lowvoltage", "sockets", "future", "panels")
            }
            session.add_all(categories.values())
            await session.flush()
            for sku, slug, specs in (
                ("QA-1", "lowvoltage", {CURRENT: "16 A", CODE: "QA-1", EXTRA: "A"}),
                ("QA-2", "lowvoltage", {CURRENT: "32 A", CODE: "QA-2", EXTRA: "B"}),
                ("QA-3", "sockets", {CURRENT: "16 A", "Колір": "Чорний"}),
                ("QA-4", "future", {EXTRA: "C"}),
            ):
                session.add(
                    Product(
                        sku=sku,
                        slug=sku.lower(),
                        name=sku,
                        brand="QA",
                        category_id=categories[slug].id,
                        price=Decimal("100"),
                        stock_status=StockStatus.PREORDER,
                        attributes=[
                            ProductAttribute(
                                key=key,
                                value=value,
                                source=ProductAttributeSource.PRIMARY,
                                position=position,
                            )
                            for position, (key, value) in enumerate(specs.items())
                        ],
                    )
                )
            await session.commit()
            yield UnitOfWork(session)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_filter_configuration_is_dry_run_by_default(filter_uow: UnitOfWork):
    result = await configure_category_filters(filter_uow.session)
    assert result.attributes_created == 2
    assert result.assignments_created == 3
    assert set(result.categories) == {"lowvoltage", "sockets"}
    for model in (CatalogAttribute, CategoryAttribute):
        assert (
            await filter_uow.session.scalar(select(func.count()).select_from(model))
            == 0
        )


@pytest.mark.asyncio
async def test_filter_configuration_is_idempotent_and_preserves_supplier_data(
    filter_uow: UnitOfWork,
):
    snapshot_query = select(
        ProductAttribute.id,
        ProductAttribute.product_id,
        ProductAttribute.key,
        ProductAttribute.value,
        ProductAttribute.source,
        ProductAttribute.position,
        ProductAttribute.attribute_id,
    ).order_by(ProductAttribute.id)
    before = (await filter_uow.session.execute(snapshot_query)).all()
    first = await configure_category_filters(filter_uow.session, dry_run=False)
    assert first.attributes_created == 2 and first.assignments_created == 3
    second = await configure_category_filters(filter_uow.session, dry_run=False)
    assert second.attributes_created == 0 and second.assignments_created == 0
    assert (await filter_uow.session.execute(snapshot_query)).all() == before
    assert set(await filter_uow.session.scalars(select(CatalogAttribute.name))) == {
        CURRENT,
        "Колір",
    }


@pytest.mark.asyncio
async def test_curated_keys_respect_categories_and_unconfigured_category_fallback(
    filter_uow: UnitOfWork,
):
    await configure_category_filters(filter_uow.session, dry_run=False)
    service = CatalogQueryService(filter_uow)
    keys = await service.get_spec_facets(SpecFacetParams(category="lowvoltage"))
    assert [item.value for item in keys.items] == [CURRENT]
    assert keys.items[0].count == 2
    assert not keys.has_next
    socket_keys = await service.get_spec_facets(SpecFacetParams(category="sockets"))
    assert {item.value for item in socket_keys.items} == {CURRENT, "Колір"}
    future_keys = await service.get_spec_facets(SpecFacetParams(category="future"))
    assert [item.value for item in future_keys.items] == [EXTRA]
    legacy = await service.get_products(
        ProductListParams(category="lowvoltage", include_facets=True)
    )
    assert set(legacy.facets.specs) == {CURRENT}
    assert legacy.total == 2
    assert EXTRA in legacy.items[0].specs and CODE in legacy.items[0].specs


@pytest.mark.asyncio
async def test_existing_links_to_uncurated_specs_remain_filterable(
    filter_uow: UnitOfWork,
):
    await configure_category_filters(filter_uow.session, dry_run=False)
    service = CatalogQueryService(filter_uow)
    spec = json.dumps([CODE, "QA-1"])
    products = await service.get_products(
        ProductListParams(category="lowvoltage", spec=[spec], include_facets=False)
    )
    assert products.total == 1 and products.items[0].sku == "QA-1"
    values = await service.get_spec_facets(
        SpecFacetParams(category="lowvoltage", facet_key=CODE, spec=[spec])
    )
    assert {item.value for item in values.items} == {"QA-1", "QA-2"}
    assert all(item.count == 1 for item in values.items)


@pytest.mark.asyncio
async def test_normalized_material_and_ip_filters_use_supplier_attributes(
    filter_uow: UnitOfWork,
):
    panels = await filter_uow.session.scalar(
        select(Category).where(Category.slug == "panels")
    )
    assert panels is not None
    sockets = await filter_uow.session.scalar(
        select(Category).where(Category.slug == "sockets")
    )
    assert sockets is not None
    filter_uow.session.add_all(
        (
            Product(
                sku="PANEL-METAL",
                slug="panel-metal",
                name="Металевий щит IP31",
                brand="QA",
                category_id=panels.id,
                price=Decimal("100"),
                stock_status=StockStatus.PREORDER,
                attributes=[
                    ProductAttribute(key="Матеріал", value="метал"),
                    ProductAttribute(key="Ступінь захисту, IP", value="ІР31"),
                ],
            ),
            Product(
                sku="PANEL-ABS",
                slug="panel-abs",
                name="Щит ABS IP65",
                brand="QA",
                category_id=panels.id,
                price=Decimal("100"),
                stock_status=StockStatus.PREORDER,
                attributes=[
                    ProductAttribute(
                        key="Матеріал виготовлення", value="Корпус – ABS - пластик"
                    ),
                    ProductAttribute(key="Ступінь захисту IP", value="IP65"),
                ],
            ),
            Product(
                sku="PANEL-MIXED",
                slug="panel-mixed",
                name="Комбінований щит IP20",
                brand="QA",
                category_id=panels.id,
                price=Decimal("100"),
                stock_status=StockStatus.PREORDER,
                attributes=[
                    ProductAttribute(key="Матеріал", value="Пластик/метал"),
                    ProductAttribute(key="Ступінь захисту IP", value="IP20"),
                ],
            ),
            Product(
                sku="SOCKET-METAL",
                slug="socket-metal",
                name="Металева розетка",
                brand="QA",
                category_id=sockets.id,
                price=Decimal("100"),
                stock_status=StockStatus.PREORDER,
                attributes=[ProductAttribute(key="Матеріал", value="метал")],
            ),
        )
    )
    await filter_uow.session.flush()
    service = CatalogQueryService(filter_uow)

    materials = await service.get_spec_facets(
        SpecFacetParams(category="panels", facet_key="Матеріал")
    )
    assert {item.value: item.count for item in materials.items} == {
        "Метал": 2,
        "Пластик": 1,
        "АБС-пластик": 1,
    }
    protection = await service.get_spec_facets(
        SpecFacetParams(category="panels", facet_key="Ступінь захисту IP")
    )
    assert {item.value: item.count for item in protection.items} == {
        "IP20": 1,
        "IP31": 1,
        "IP65": 1,
    }

    selected_materials = await service.get_products(
        ProductListParams(
            category="panels",
            spec=[
                json.dumps(["Матеріал", "Метал"]),
                json.dumps(["Матеріал", "Пластик"]),
            ],
        )
    )
    assert {item.sku for item in selected_materials.items} == {
        "PANEL-METAL",
        "PANEL-MIXED",
    }
    selected_ip = await service.get_products(
        ProductListParams(
            category="panels", spec=[json.dumps(["Ступінь захисту IP", "IP31"])]
        )
    )
    assert [item.sku for item in selected_ip.items] == ["PANEL-METAL"]

    raw_global_material = await service.get_products(
        ProductListParams(spec=[json.dumps(["Матеріал", "метал"])])
    )
    assert {item.sku for item in raw_global_material.items} == {
        "PANEL-METAL",
        "SOCKET-METAL",
    }


@pytest.mark.asyncio
async def test_curated_counts_deduplicate_sources_and_exclude_own_selection(
    filter_uow: UnitOfWork,
):
    product = await filter_uow.products.get_by_sku("QA-1")
    assert product is not None
    product.attributes.append(
        ProductAttribute(
            key=CURRENT,
            value="16 A",
            source=ProductAttributeSource.ETIM,
            position=10,
        )
    )
    await filter_uow.session.flush()
    await configure_category_filters(filter_uow.session, dry_run=False)
    values = await CatalogQueryService(filter_uow).get_spec_facets(
        SpecFacetParams(
            category="lowvoltage",
            facet_key=CURRENT,
            spec=[json.dumps([CURRENT, "16 A"])],
        )
    )
    assert {item.value: item.count for item in values.items} == {"16 A": 1, "32 A": 1}


@pytest.mark.asyncio
async def test_configuration_preserves_manual_flags_and_disabled_definitions(
    filter_uow: UnitOfWork,
):
    await configure_category_filters(filter_uow.session, dry_run=False)
    definition = await filter_uow.session.scalar(
        select(CatalogAttribute).where(CatalogAttribute.name == CURRENT)
    )
    assert definition is not None
    definition.is_filterable = False
    assignments = (
        await filter_uow.session.scalars(
            select(CategoryAttribute).where(
                CategoryAttribute.attribute_id == definition.id
            )
        )
    ).all()
    for assignment in assignments:
        assignment.is_required = True
        assignment.position = 42
    await filter_uow.session.flush()
    await configure_category_filters(filter_uow.session, dry_run=False)
    assert not definition.is_filterable
    assert all(a.is_required and a.position == 42 for a in assignments)
    keys = await CatalogQueryService(filter_uow).get_spec_facets(
        SpecFacetParams(category="lowvoltage")
    )
    assert not keys.items


@pytest.mark.asyncio
async def test_curated_metadata_keeps_free_form_specs_editable(filter_uow: UnitOfWork):
    await configure_category_filters(filter_uow.session, dry_run=False)
    product = await filter_uow.products.get_by_sku("QA-1")
    assert product is not None
    result = await ProductManagementService(filter_uow).update_product(
        product.id,
        UpdateProductRequest(specs={CURRENT: "16 A", CODE: "QA-1", EXTRA: "Edited"}),
    )
    assert result.specs == {CURRENT: "16 A", CODE: "QA-1", EXTRA: "Edited"}


@pytest.mark.asyncio
async def test_required_definitions_still_validate_free_form_edits(
    filter_uow: UnitOfWork,
):
    await configure_category_filters(filter_uow.session, dry_run=False)
    product = await filter_uow.products.get_by_sku("QA-1")
    assert product is not None
    assignment = await filter_uow.session.scalar(
        select(CategoryAttribute).where(
            CategoryAttribute.category_id == product.category_id
        )
    )
    assert assignment is not None
    assignment.is_required = True
    await filter_uow.session.flush()
    with pytest.raises(UnprocessableError) as caught:
        await ProductManagementService(filter_uow).update_product(
            product.id, UpdateProductRequest(specs={EXTRA: "Still supported"})
        )
    assert caught.value.code == "required_product_attribute_missing"
