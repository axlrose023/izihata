from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.modules.catalog.models import Category
from app.database.base import Base


@pytest.mark.parametrize(
    "category_id",
    [
        UUID("1e999999-9999-4999-8999-999999999999"),
        UUID("12345678-1234-4123-8123-123456789012"),
    ],
)
@pytest.mark.asyncio
async def test_uuid_primary_keys_cannot_be_coerced_to_sqlite_numbers(category_id):
    engine = create_async_engine("sqlite+aiosqlite://")
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with async_sessionmaker(engine)() as session:
            session.add(Category(id=category_id, slug="qa", name="QA"))
            await session.commit()
            session.expunge_all()
            category = await session.get(Category, category_id)
            assert category is not None
            assert category.id == category_id
    finally:
        await engine.dispose()
