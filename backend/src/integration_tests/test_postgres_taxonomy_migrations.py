"""Exercise taxonomy changes and exact rollback in an isolated PostgreSQL schema."""

import importlib.util
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.api.modules.catalog.models import Category, Product, Subcategory
from app.database.base import Base
from app.database.engine import engine

pytestmark = pytest.mark.integration


def migration(filename):
    path = Path(__file__).parents[1] / "app/database/migrations/versions" / filename
    spec = importlib.util.spec_from_file_location("taxonomy_test_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def snapshot(connection):
    return {
        table.name: connection.execute(select(table).order_by(table.c.id)).all()
        for table in (Product.__table__, Subcategory.__table__)
    }


def exercise_original(connection):
    with Session(connection, join_transaction_mode="create_savepoint") as session:
        categories = {
            slug: Category(slug=slug, name=slug)
            for slug in (
                "lowvoltage",
                "panels",
                "light",
                "installation",
                "other",
                "power",
            )
        }
        session.add_all(categories.values())
        session.flush()
        for index, name in enumerate(
            (
                "Автоматичні вимикачі (модульні / корпусні / повітряні)",
                "Додаткові пристрої до автоматів",
                "Диференціальні автомати",
                "Автомати захисту двигуна",
            )
        ):
            session.add(
                Subcategory(
                    category_id=categories["lowvoltage"].id,
                    slug=f"legacy-{index}",
                    name=name,
                )
            )
        for index, name in enumerate(
            (
                "Повітряний автоматичний вимикач",
                "Силовий автоматичний вимикач",
                "\u0410\u0412\u0420 100\u0410",
                "Блок живлення 12\u0412",
                "ЯТП 220/12\u0412",
            )
        ):
            session.add(
                Product(
                    sku=f"TEST-{index}",
                    slug=f"test-{index}",
                    name=name,
                    brand="QA",
                    category_id=categories["other"].id,
                    price=123.45,
                )
            )
        session.flush()
        before = snapshot(connection)
        module = migration("2026_10_07_1200_refine_catalog_taxonomy.py")
        with Operations.context(MigrationContext.configure(connection)):
            with pytest.raises(RuntimeError, match="no original category snapshot"):
                module.downgrade()
            assert snapshot(connection) == before
            module.upgrade()
            assert snapshot(connection) != before
            module.downgrade()
            assert snapshot(connection) == before


@pytest.mark.parametrize("exercise", [exercise_original])
@pytest.mark.asyncio(loop_scope="session")
async def test_taxonomy_migrations_restore_original_rows(exercise):
    schema = f"taxonomy_test_{uuid4().hex}"
    async with engine.begin() as connection:
        # Random identifier is generated here, never supplied by a caller.
        await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        await connection.execute(text(f'SET LOCAL search_path TO "{schema}", public'))
        await connection.run_sync(
            lambda sync_connection: Base.metadata.create_all(
                sync_connection, checkfirst=False
            )
        )
        await connection.run_sync(exercise)
        await connection.execute(text("SET LOCAL search_path TO public"))
        await connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
