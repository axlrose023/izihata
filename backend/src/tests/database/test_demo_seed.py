import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.modules.catalog.models import (
    Category,
    Product,
    ProductDocument,
    ProductMedia,
    ProductRelation,
)
from app.database.seed import seed_database


@pytest.mark.asyncio
async def test_demo_catalog_seed_is_repeatable(session: AsyncSession) -> None:
    await seed_database(session)
    await seed_database(session)

    product_id = await session.scalar(
        select(Product.id).where(Product.sku == "DEMO-MCB-16")
    )
    assert product_id is not None

    media_count = await session.scalar(
        select(func.count())
        .select_from(ProductMedia)
        .where(ProductMedia.product_id == product_id)
    )
    document_count = await session.scalar(
        select(func.count())
        .select_from(ProductDocument)
        .where(ProductDocument.product_id == product_id)
    )
    relation_count = await session.scalar(
        select(func.count())
        .select_from(ProductRelation)
        .where(ProductRelation.source_product_id == product_id)
    )
    category_names = set((await session.scalars(select(Category.name))).all())

    assert media_count == 2
    assert document_count == 1
    assert relation_count == 1
    assert {"Альтернативна енергія", "Кліматичне обладнання"} <= category_names
