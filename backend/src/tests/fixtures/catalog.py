import pytest_asyncio
from sqlalchemy import select

from app.api.modules.catalog.models import Product
from app.database.uow import UnitOfWork


@pytest_asyncio.fixture
async def product(uow: UnitOfWork) -> Product:
    result = await uow.session.execute(select(Product).where(Product.sku == "AX-10001"))
    return result.scalar_one()
