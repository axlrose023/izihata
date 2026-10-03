from uuid import UUID

import pytest
from sqlalchemy import event, select

from app.api.modules.catalog.enums import ProductRelationKind
from app.api.modules.catalog.models import Product, ProductRelation


@pytest.mark.asyncio
async def test_related_groups_share_queries_and_keep_independent_limits(
    uow, temporary_product, engine
):
    source_id = UUID(temporary_product["id"])
    targets = list(
        (
            await uow.session.scalars(
                select(Product)
                .where(Product.id != source_id, Product.is_active.is_(True))
                .order_by(Product.id)
                .limit(10)
            )
        ).all()
    )
    assert len(targets) == 10
    for kind in ProductRelationKind:
        for position, target in enumerate(targets):
            uow.session.add(
                ProductRelation(
                    source_product_id=source_id,
                    target_product_id=target.id,
                    kind=kind,
                    position=position,
                )
            )
    targets[0].is_active = False
    await uow.session.flush()
    statements = []

    def record(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", record)
    try:
        rows = await uow.products.list_related_groups(source_id)
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", record)
    assert len(statements) == 2  # One relation query and one shared attributes query.
    for kind in ProductRelationKind:
        assert [product.id for group, product in rows if group == kind] == [
            product.id for product in targets[1:9]
        ]
    # No commit: fixture rolls back this test's relations and visibility changes.
