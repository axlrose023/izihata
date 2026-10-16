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


def exercise_reviewed(connection):
    with Session(connection, join_transaction_mode="create_savepoint") as session:
        categories = {
            slug: Category(slug=slug, name=slug)
            for slug in ("lowvoltage", "panels", "cabletrays", "other")
        }
        session.add_all(categories.values())
        session.flush()
        avr = Subcategory(
            category_id=categories["panels"].id,
            slug="panels-14",
            name="\u0410\u0412\u0420 (автоматичний ввід резерву)",
            position=13,
        )
        holders = Subcategory(
            category_id=categories["cabletrays"].id,
            slug="cabletrays-6",
            name="Кабельні тримачі",
        )
        session.add_all([avr, holders])
        session.flush()
        session.add_all(
            [
                Product(
                    sku="s015097",
                    slug="base",
                    name="Основа під кабельну стяжку",
                    brand="QA",
                    category_id=categories["other"].id,
                    price=123.45,
                ),
                Product(
                    sku="TEST-AVR",
                    slug="avr",
                    name="\u0410\u0412\u0420 100\u0410",
                    brand="QA",
                    category_id=categories["panels"].id,
                    subcategory_id=avr.id,
                    price=123.45,
                ),
                Product(
                    sku="UNRELATED",
                    slug="unchanged",
                    name="Unchanged",
                    brand="QA",
                    category_id=categories["other"].id,
                    price=123.45,
                ),
            ]
        )
        session.flush()
        before = snapshot(connection)
        module = migration("2026_10_07_1900_correct_reviewed_taxonomy_assignments.py")
        with Operations.context(MigrationContext.configure(connection)):
            module.upgrade()
            assignments = dict(
                connection.execute(select(Product.sku, Product.category_id)).all()
            )
            assert assignments["s015097"] == categories["cabletrays"].id
            assert assignments["TEST-AVR"] == categories["lowvoltage"].id
            assert assignments["UNRELATED"] == categories["other"].id
            module.downgrade()
            assert snapshot(connection) == before


def exercise_requested(connection):
    with Session(connection, join_transaction_mode="create_savepoint") as session:
        categories = {
            slug: Category(slug=slug, name=slug)
            for slug in (
                "lowvoltage",
                "relay",
                "installation",
                "cabletrays",
                "other",
                "switching",
            )
        }
        session.add_all(categories.values())
        session.flush()
        old_relays = Subcategory(
            category_id=categories["relay"].id,
            slug="relay-6",
            name="Допоміжні реле",
            position=5,
        )
        contactors = Subcategory(
            category_id=categories["lowvoltage"].id,
            slug="lowvoltage-7",
            name="Контактори",
            position=6,
        )
        session.add_all([old_relays, contactors])
        session.flush()
        session.add_all(
            [
                Product(
                    sku="TEST-RELAY",
                    slug="test-relay",
                    name="Проміжне реле VS116K",
                    brand="QA",
                    category_id=categories["relay"].id,
                    subcategory_id=old_relays.id,
                    price=123.45,
                ),
                Product(
                    sku="TEST-COIL",
                    slug="test-coil",
                    name="Котушка управління контактора 24\u0412",
                    brand="QA",
                    category_id=categories["relay"].id,
                    price=123.45,
                ),
                Product(
                    sku="TEST-THERMAL",
                    slug="test-thermal",
                    name="Теплове реле RE 17D-0,4",
                    brand="QA",
                    category_id=categories["relay"].id,
                    price=123.45,
                ),
                Product(
                    sku="TEST-THERMAL-ALT",
                    slug="test-thermal-alt",
                    name="Реле теплове \u0420\u0422\u041a\u041c 90-120 \u0410",
                    brand="QA",
                    category_id=categories["relay"].id,
                    price=123.45,
                ),
                Product(
                    sku="TEST-ACCESSORY",
                    slug="test-accessory",
                    name="Блок реверса контактора AR85",
                    brand="QA",
                    category_id=categories["installation"].id,
                    price=123.45,
                ),
                Product(
                    sku="TEST-MARKER",
                    slug="test-marker",
                    name="Комплект кабельного маркування тип \u041c-0",
                    brand="QA",
                    category_id=categories["other"].id,
                    price=123.45,
                ),
                Product(
                    sku="TEST-SIP",
                    slug="test-sip",
                    name="Відгалужувальний проколюючий затискач AsXS",
                    brand="QA",
                    category_id=categories["other"].id,
                    price=123.45,
                ),
                Product(
                    sku="TEST-WELL",
                    slug="test-well",
                    name="Колодязь кабельний пластиковий",
                    brand="QA",
                    category_id=categories["other"].id,
                    price=123.45,
                ),
                Product(
                    sku="TEST-CONTACTOR",
                    slug="test-contactor",
                    name="Модульний контактор MK-N 1P 16A",
                    brand="QA",
                    category_id=categories["switching"].id,
                    price=123.45,
                ),
                Product(
                    sku="TEST-UNRELATED",
                    slug="test-unrelated",
                    name="Unchanged",
                    brand="QA",
                    category_id=categories["other"].id,
                    price=123.45,
                ),
            ]
        )
        session.flush()
        before = snapshot(connection)
        module = migration(
            "2026_10_16_1200_add_requested_catalog_subcategories.py"
        )
        with Operations.context(MigrationContext.configure(connection)):
            module.upgrade()
            subcategories = {
                tuple(row)
                for row in connection.execute(
                    select(Subcategory.category_id, Subcategory.name)
                )
            }
            assert {
                (categories["lowvoltage"].id, "Котушки управління до контакторів"),
                (categories["lowvoltage"].id, "Додаткове обладнання для контакторів"),
                (categories["lowvoltage"].id, "Теплові реле"),
                (categories["relay"].id, "Реле захисту двигуна"),
                (categories["relay"].id, "Імпульсні реле"),
                (categories["relay"].id, "Розеточні реле"),
                (categories["installation"].id, "Блоки розподільчі"),
                (categories["installation"].id, "Ізолятори"),
                (categories["installation"].id, "Маркери кабельні"),
                (categories["installation"].id, "Шайби мідно-алюмінієві"),
                (categories["installation"].id, "Вироби для кріплення"),
                (categories["cabletrays"].id, "Арматура СІП"),
                (categories["cabletrays"].id, "Аксесуари для труб ПВХ"),
                (categories["cabletrays"].id, "Колодязі кабельні"),
            } <= subcategories
            assignments = {
                sku: (category_id, subcategory_id)
                for sku, category_id, subcategory_id in connection.execute(
                    select(Product.sku, Product.category_id, Product.subcategory_id)
                )
            }
            assert (categories["relay"].id, "Допоміжні реле") not in subcategories
            assert (categories["relay"].id, "Проміжні реле") in subcategories
            assert assignments["TEST-RELAY"] == (
                categories["relay"].id,
                old_relays.id,
            )
            assert assignments["TEST-COIL"][0] == categories["lowvoltage"].id
            assert assignments["TEST-THERMAL"][0] == categories["lowvoltage"].id
            assert assignments["TEST-THERMAL-ALT"][0] == categories["relay"].id
            assert assignments["TEST-ACCESSORY"][0] == categories["lowvoltage"].id
            assert assignments["TEST-MARKER"][0] == categories["installation"].id
            assert assignments["TEST-SIP"][0] == categories["cabletrays"].id
            assert assignments["TEST-WELL"][0] == categories["cabletrays"].id
            assert assignments["TEST-CONTACTOR"] == (
                categories["lowvoltage"].id,
                contactors.id,
            )
            assert assignments["TEST-UNRELATED"][0] == categories["other"].id
            adjustment = migration(
                "2026_10_16_1330_complete_thermal_relay_assignment.py"
            )
            adjustment.upgrade()
            assert connection.execute(
                select(Product.category_id).where(Product.sku == "TEST-THERMAL-ALT")
            ).scalar_one() == categories["lowvoltage"].id
            adjustment.downgrade()
            module.downgrade()
            assert snapshot(connection) == before


@pytest.mark.parametrize(
    "exercise", [exercise_original, exercise_reviewed, exercise_requested]
)
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
