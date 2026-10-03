from uuid import UUID, uuid4

import pytest_asyncio
from sqlalchemy import delete, select

from app.api.modules.catalog.models import Product
from app.database.uow import UnitOfWork


@pytest_asyncio.fixture
async def product(uow: UnitOfWork) -> Product:
    result = await uow.session.execute(select(Product).where(Product.sku == "AX-10001"))
    return result.scalar_one()


@pytest_asyncio.fixture
async def temporary_product(request, client, authenticated_user, product, session):
    headers = {"Authorization": f"Bearer {authenticated_user['access_token']}"}
    response = await client.post(
        "/api/v1/admin/catalog/products",
        headers=headers,
        json={
            "category_id": str(product.category_id),
            "sku": "audit-" + uuid4().hex,
            "name": "Isolated audit product",
            "brand": product.brand,
            "price": "100.00",
            **getattr(request, "param", {}),
        },
    )
    assert response.status_code == 201, response.text
    created = response.json()
    try:
        yield created
    finally:
        await session.execute(delete(Product).where(Product.id == UUID(created["id"])))
        await session.commit()
